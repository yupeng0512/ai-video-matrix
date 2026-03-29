"""Content Planner API — LLM-driven script variant factory."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, engine
from models import Base, Product, ScriptVariant, HookType, StyleType, DurationType, ScriptStatus
from generator import generate_script, generate_batch


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Content Planner", lifespan=lifespan)


# ── Schemas ──────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = []


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    keywords: list[str] | None
    script_count: int = 0


class ScriptGenRequest(BaseModel):
    product_id: uuid.UUID
    hook: HookType
    style: StyleType
    duration: DurationType


class BatchGenRequest(BaseModel):
    product_id: uuid.UUID
    count: int = 20


class ScriptOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    hook: str
    style: str
    duration: str
    prompt_text: str
    visual_desc: str | None
    tts_text: str | None
    status: str


# ── Products ─────────────────────────────────────────────────

@app.post("/products", response_model=ProductOut)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = Product(name=body.name, description=body.description, keywords=body.keywords)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductOut(id=product.id, name=product.name, description=product.description, keywords=product.keywords)


@app.get("/products", response_model=list[ProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    stmt = select(Product).order_by(Product.created_at.desc())
    result = await db.execute(stmt)
    products = result.scalars().all()
    out = []
    for p in products:
        count_stmt = select(func.count()).select_from(ScriptVariant).where(ScriptVariant.product_id == p.id)
        count_result = await db.execute(count_stmt)
        cnt = count_result.scalar() or 0
        out.append(ProductOut(id=p.id, name=p.name, description=p.description, keywords=p.keywords, script_count=cnt))
    return out


# ── Script Generation ────────────────────────────────────────

@app.post("/scripts/generate", response_model=ScriptOut)
async def gen_single_script(body: ScriptGenRequest, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, body.product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    result = await generate_script(
        product.name, product.description or "", product.keywords or [],
        body.hook, body.style, body.duration,
    )

    sv = ScriptVariant(
        product_id=product.id,
        hook=body.hook,
        style=body.style,
        duration=body.duration,
        prompt_text=result.get("prompt_text", ""),
        visual_desc=result.get("visual_desc"),
        tts_text=result.get("tts_text"),
        status=ScriptStatus.ready,
    )
    db.add(sv)
    await db.commit()
    await db.refresh(sv)

    return ScriptOut(
        id=sv.id, product_id=sv.product_id,
        hook=sv.hook.value, style=sv.style.value, duration=sv.duration.value,
        prompt_text=sv.prompt_text, visual_desc=sv.visual_desc, tts_text=sv.tts_text,
        status=sv.status.value,
    )


@app.post("/scripts/generate-batch", response_model=list[ScriptOut])
async def gen_batch_scripts(body: BatchGenRequest, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, body.product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    scripts_out = []
    async for result in generate_batch(
        product.name, product.description or "", product.keywords or [], count=body.count,
    ):
        sv = ScriptVariant(
            product_id=product.id,
            hook=HookType(result["hook"]),
            style=StyleType(result["style"]),
            duration=DurationType(result["duration"]),
            prompt_text=result.get("prompt_text", ""),
            visual_desc=result.get("visual_desc"),
            tts_text=result.get("tts_text"),
            status=ScriptStatus.ready,
        )
        db.add(sv)
        await db.flush()
        scripts_out.append(ScriptOut(
            id=sv.id, product_id=sv.product_id,
            hook=sv.hook.value, style=sv.style.value, duration=sv.duration.value,
            prompt_text=sv.prompt_text, visual_desc=sv.visual_desc, tts_text=sv.tts_text,
            status=sv.status.value,
        ))

    await db.commit()
    return scripts_out


@app.get("/scripts", response_model=list[ScriptOut])
async def list_scripts(
    product_id: uuid.UUID | None = None,
    status: ScriptStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ScriptVariant).order_by(ScriptVariant.created_at.desc()).limit(limit)
    if product_id:
        stmt = stmt.where(ScriptVariant.product_id == product_id)
    if status:
        stmt = stmt.where(ScriptVariant.status == status)
    result = await db.execute(stmt)
    scripts = result.scalars().all()
    return [
        ScriptOut(
            id=s.id, product_id=s.product_id,
            hook=s.hook.value, style=s.style.value, duration=s.duration.value,
            prompt_text=s.prompt_text, visual_desc=s.visual_desc, tts_text=s.tts_text,
            status=s.status.value,
        )
        for s in scripts
    ]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "content-planner"}
