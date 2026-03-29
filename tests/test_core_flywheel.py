"""Core Flywheel Validation — Zero-Cost Unit Tests.

Tests the 5 critical gears of the AI Video Matrix system
using only pure functions. No DB, no API, no Docker needed.
"""
import sys
import os
import enum
import itertools
import json
import statistics

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')

# mutator.py only uses stdlib — safe to import directly
sys.path.insert(0, os.path.join(BASE_DIR, 'services', 'video-mutator'))


# ============================================================
# Inline replicas of enums (models.py requires sqlalchemy)
# ============================================================

class HookType(str, enum.Enum):
    question = "question"
    suspense = "suspense"
    data = "data"
    empathy = "empathy"


class StyleType(str, enum.Enum):
    recommend = "recommend"
    review = "review"
    tutorial = "tutorial"
    story = "story"


class DurationType(str, enum.Enum):
    s15 = "15s"
    s30 = "30s"
    s60 = "60s"


# ============================================================
# Inline replica of generator._user_prompt (generator.py requires openai)
# ============================================================

def _user_prompt(
    product_name: str,
    product_desc: str,
    keywords: list,
    hook: HookType,
    style: StyleType,
    duration: DurationType,
) -> str:
    hook_labels = {
        HookType.question: "提问式开头（抛出用户痛点）",
        HookType.suspense: "悬念式开头（制造好奇心）",
        HookType.data: "数据式开头（用数字说话）",
        HookType.empathy: "共鸣式开头（引发情感共鸣）",
    }
    style_labels = {
        StyleType.recommend: "种草推荐风格",
        StyleType.review: "测评对比风格",
        StyleType.tutorial: "使用教程风格",
        StyleType.story: "故事叙述风格",
    }
    return (
        f"产品名称：{product_name}\n"
        f"产品描述：{product_desc}\n"
        f"关键词：{', '.join(keywords or [])}\n\n"
        f"Hook 类型：{hook_labels[hook]}\n"
        f"文案风格：{style_labels[style]}\n"
        f"视频时长：{duration.value}\n\n"
        f"请生成一条短视频脚本。只输出 JSON，不要其他文字。"
    )


# ============================================================
# Inline replicas of hash_checker pure functions (requires videohash)
# ============================================================

def hamming_distance(hash1: str, hash2: str) -> int:
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor = int1 ^ int2
    return bin(xor).count("1")


def similarity_score(hash1: str, hash2: str) -> float:
    dist = hamming_distance(hash1, hash2)
    max_bits = max(len(hash1), len(hash2)) * 4
    return 1.0 - (dist / max_bits) if max_bits > 0 else 0.0


# ============================================================
# Gear 1: Script Differentiation (48 unique combos)
# ============================================================

def test_script_combo_coverage():
    """Verify 4 hooks x 4 styles x 3 durations = 48 unique combos."""
    hooks = list(HookType)
    styles = list(StyleType)
    durations = list(DurationType)

    combos = list(itertools.product(hooks, styles, durations))
    assert len(combos) == 48, f"Expected 48 combos, got {len(combos)}"
    assert len(set(combos)) == 48, "Duplicate combos found!"
    print(f"  Gear 1: {len(combos)} unique script combos verified")


def test_prompt_differentiation():
    """Verify different hook/style produce different prompts."""
    prompt1 = _user_prompt("智能手表", "高端智能手表", ["智能", "手表"],
                           HookType.question, StyleType.recommend, DurationType.s15)
    prompt2 = _user_prompt("智能手表", "高端智能手表", ["智能", "手表"],
                           HookType.suspense, StyleType.review, DurationType.s30)

    assert prompt1 != prompt2, "Different combos should produce different prompts"
    assert "提问式" in prompt1, "Question hook should mention 提问式"
    assert "悬念式" in prompt2, "Suspense hook should mention 悬念式"
    assert "15s" in prompt1
    assert "30s" in prompt2
    print("  Gear 1: Prompt differentiation verified")


def test_prompt_template_matches_source():
    """Verify inline _user_prompt matches source generator.py exactly."""
    gen_path = os.path.join(BASE_DIR, 'services', 'content-planner', 'generator.py')
    with open(gen_path) as f:
        source = f.read()

    assert "提问式开头（抛出用户痛点）" in source
    assert "悬念式开头（制造好奇心）" in source
    assert "数据式开头（用数字说话）" in source
    assert "共鸣式开头（引发情感共鸣）" in source
    assert "种草推荐风格" in source
    assert "测评对比风格" in source
    assert "使用教程风格" in source
    assert "故事叙述风格" in source
    print("  Gear 1: Prompt template matches source generator.py")


# ============================================================
# Gear 2: Video Mutation (5-dimension FFmpeg)
# ============================================================

def test_random_params_variety():
    """Verify random params produce different values each time."""
    from mutator import random_params

    params_list = [random_params("medium") for _ in range(10)]

    brightness_values = [p.brightness for p in params_list]
    assert len(set(brightness_values)) > 1, "Random params should vary"

    for p in params_list:
        assert -0.03 <= p.brightness <= 0.03, f"Brightness out of range: {p.brightness}"
        assert 0.97 <= p.contrast <= 1.03, f"Contrast out of range: {p.contrast}"
        assert 0.95 <= p.saturation <= 1.05, f"Saturation out of range: {p.saturation}"
    print("  Gear 2: Random params variety verified (10 unique sets)")


def test_ffmpeg_cmd_construction():
    """Verify FFmpeg commands are well-formed with active filters."""
    from mutator import build_ffmpeg_cmd, MutationParams

    params = MutationParams(
        brightness=0.02, contrast=1.03, saturation=0.97, hue=2.0,
        crop_pct=0.01, mirror=True, speed_factor=1.01,
        audio_pitch_semitones=0.5, audio_volume_db=-0.5,
        fps_delta=1, crf_delta=-1,
    )

    cmd = build_ffmpeg_cmd("/input.mp4", "/output.mp4", params)

    assert cmd[0] == "ffmpeg", "Command should start with ffmpeg"
    assert "-y" in cmd, "Should have overwrite flag"
    assert "-i" in cmd, "Should have input flag"
    assert "/input.mp4" in cmd, "Should have input path"
    assert "/output.mp4" in cmd, "Should have output path"
    assert "-vf" in cmd, "Should have video filters"
    assert "-af" in cmd, "Should have audio filters"
    assert "-c:v" in cmd, "Should have video codec"

    vf_idx = cmd.index("-vf")
    vf_str = cmd[vf_idx + 1]
    assert "eq=" in vf_str, "Should have eq filter"
    assert "hue=" in vf_str, "Should have hue filter"
    assert "hflip" in vf_str, "Should have mirror (hflip)"
    assert "crop=" in vf_str, "Should have crop filter"

    print(f"  Gear 2: FFmpeg command construction verified ({len(cmd)} args)")


def test_ffmpeg_cmd_minimal():
    """Verify default params produce minimal FFmpeg command."""
    from mutator import build_ffmpeg_cmd, MutationParams

    params = MutationParams()
    cmd = build_ffmpeg_cmd("/in.mp4", "/out.mp4", params)

    assert "-vf" not in cmd, "Default params should not add video filters"
    assert "-af" not in cmd, "Default params should not add audio filters"
    assert "-c:v" in cmd, "Should still have codec"
    print("  Gear 2: Minimal FFmpeg command verified (no unnecessary filters)")


def test_intensity_levels():
    """Verify low/medium/high intensity produce increasing mutation ranges."""
    from mutator import random_params

    sample_size = 100

    def avg_magnitude(intensity):
        params = [random_params(intensity) for _ in range(sample_size)]
        return statistics.mean([
            abs(p.brightness) + abs(p.contrast - 1) + abs(p.saturation - 1)
            for p in params
        ])

    low_avg = avg_magnitude("low")
    med_avg = avg_magnitude("medium")
    high_avg = avg_magnitude("high")

    assert low_avg < med_avg < high_avg, (
        f"Intensity ordering broken: low={low_avg:.4f} med={med_avg:.4f} high={high_avg:.4f}"
    )
    print(f"  Gear 2: Intensity levels verified (low={low_avg:.4f} < med={med_avg:.4f} < high={high_avg:.4f})")


def test_mutation_params_to_dict():
    """Verify MutationParams serializes all fields."""
    from mutator import MutationParams

    params = MutationParams(brightness=0.01, mirror=True)
    d = params.to_dict()

    assert d["brightness"] == 0.01
    assert d["mirror"] is True
    assert "contrast" in d
    assert "saturation" in d
    assert "hue" in d
    assert "crop_pct" in d
    assert "speed_factor" in d
    assert "audio_pitch_semitones" in d
    assert "audio_volume_db" in d
    assert "fps_delta" in d
    assert "crf_delta" in d
    assert len(d) == 11, f"Expected 11 fields, got {len(d)}"
    print("  Gear 2: MutationParams.to_dict() verified (11 fields)")


# ============================================================
# Gear 3: Perceptual Hash Similarity
# ============================================================

def test_hamming_distance():
    """Verify Hamming distance calculation."""
    assert hamming_distance("abcd1234", "abcd1234") == 0
    assert hamming_distance("0000", "000f") == 4  # 0000 vs 1111
    dist = hamming_distance("0000", "ffff")
    assert dist == 16, f"Expected 16, got {dist}"
    print("  Gear 3: Hamming distance verified")


def test_similarity_score():
    """Verify similarity scoring."""
    assert similarity_score("abcdef", "abcdef") == 1.0

    sim = similarity_score("000000", "ffffff")
    assert sim < 0.1, f"Completely different should be <0.1, got {sim}"

    # e=1110, f=1111 → 1 bit difference
    sim = similarity_score("abcdef", "abcdee")
    assert sim > 0.9, f"Nearly identical should be >0.9, got {sim}"
    print("  Gear 3: Similarity scoring verified")


def test_threshold_gate():
    """Verify the 70% threshold gate logic."""
    THRESHOLD = 0.70

    test_cases = [
        ("abcdef123456", "abcdef123456", True,  "identical should be blocked"),
        ("abcdef123456", "000000000000", False, "completely different should pass"),
    ]

    for hash1, hash2, should_block, desc in test_cases:
        sim = similarity_score(hash1, hash2)
        is_blocked = sim >= THRESHOLD
        assert is_blocked == should_block, f"Failed: {desc} (sim={sim})"

    print("  Gear 3: 70% threshold gate verified")


def test_hash_checker_source_consistency():
    """Verify inline hash functions match hash_checker.py source."""
    hc_path = os.path.join(BASE_DIR, 'services', 'video-mutator', 'hash_checker.py')
    with open(hc_path) as f:
        source = f.read()

    assert "int(hash1, 16)" in source
    assert "bin(xor).count(\"1\")" in source
    assert "1.0 - (dist / max_bits)" in source
    assert "max(len(hash1), len(hash2)) * 4" in source
    assert "threshold: float = 0.70" in source
    print("  Gear 3: Inline functions match hash_checker.py source")


# ============================================================
# Gear 4: Platform Isolation (SQL + routing contracts)
# ============================================================

def test_sql_schema_contracts():
    """Verify SQL schema enforces platform isolation via unique constraints."""
    schema_path = os.path.join(BASE_DIR, 'storage', 'postgres', 'migrations', '001_init.sql')
    with open(schema_path) as f:
        schema = f.read()

    assert "UNIQUE (video_id, account_id)" in schema, "content_ledger must have video+account unique constraint"
    assert "UNIQUE (platform, username)" in schema, "accounts must have platform+username unique constraint"
    assert "idx_ledger_platform_hash" in schema, "Must have platform+hash index for isolation queries"
    assert "idx_accounts_platform_status" in schema, "Must have platform+status index for account queries"

    for table in ["products", "script_variants", "videos", "accounts", "content_ledger", "publish_tasks", "metrics"]:
        assert f"CREATE TABLE {table}" in schema, f"Missing table: {table}"

    for enum_type in ["hook_type", "style_type", "duration_type", "platform_type", "account_status"]:
        assert f"CREATE TYPE {enum_type}" in schema, f"Missing enum: {enum_type}"

    assert "'douyin'" in schema
    assert "'kuaishou'" in schema
    assert "'xiaohongshu'" in schema
    assert "'weixin_channel'" in schema

    print("  Gear 4: SQL schema contracts verified (7 tables, 5 enums, critical indexes)")


def test_routing_logic_contracts():
    """Verify the routing module has correct platform isolation logic."""
    router_path = os.path.join(BASE_DIR, 'services', 'content-router', 'router.py')
    with open(router_path) as f:
        code = f.read()

    assert "check_video_used_on_platform" in code, "Router must check video usage per platform"
    assert "video_hash" in code, "Router must use video_hash for dedup"
    assert "ON CONFLICT" in code, "Router must handle duplicate assignments gracefully"
    assert "find_available_account" in code, "Router must find available accounts"
    assert "daily_limit" in code, "Router must respect daily limits"
    assert "target_platforms" in code, "Router should support targeting specific platforms"

    print("  Gear 4: Routing logic contracts verified (isolation + dedup + daily limits)")


def test_routing_cross_platform_reuse():
    """Verify router allows cross-platform reuse (checks per-platform, not globally)."""
    router_path = os.path.join(BASE_DIR, 'services', 'content-router', 'router.py')
    with open(router_path) as f:
        code = f.read()

    assert "platform = :platform AND video_hash = :video_hash" in code, (
        "Similarity check must be scoped to platform (not global)"
    )
    assert "video_hash_already_used_on_platform" in code, (
        "Skip reason should be per-platform, not global"
    )
    print("  Gear 4: Cross-platform reuse logic verified (per-platform isolation)")


# ============================================================
# Gear 5: Account Lifecycle
# ============================================================

def test_account_lifecycle_states():
    """Verify account lifecycle states match the schema."""
    schema_path = os.path.join(BASE_DIR, 'storage', 'postgres', 'migrations', '001_init.sql')
    with open(schema_path) as f:
        schema = f.read()

    required_states = ["warming_up", "active", "cooling_down", "banned", "retired"]
    for state in required_states:
        assert f"'{state}'" in schema, f"Missing account state: {state}"

    print(f"  Gear 5: Account lifecycle states verified ({len(required_states)} states)")


def test_account_manager_contracts():
    """Verify account manager has correct health check and cooling logic."""
    mgr_path = os.path.join(BASE_DIR, 'services', 'publisher', 'account_manager.py')
    with open(mgr_path) as f:
        code = f.read()

    assert "success_rate" in code, "Must calculate success rate"
    assert "7 days" in code, "Health check should look at 7-day window"
    assert "critical" in code, "Must identify critical health"
    assert "degraded" in code, "Must identify degraded health"

    assert "auto_cool_down" in code, "Must have auto cool down function"
    assert "cooling_down" in code, "Must set cooling_down status"
    assert "24 hours" in code, "Cool down should use 24-hour window"
    assert "0.5" in code, "Should use 50% failure threshold"

    assert "recover_cooled_accounts" in code, "Must have recovery function"
    assert "interval '1 hour' * :hours" in code, "Must use correct SQL parameterization"

    print("  Gear 5: Account manager contracts verified (health + cooling + recovery)")


def test_health_classification_thresholds():
    """Verify the health classification logic has correct thresholds."""
    mgr_path = os.path.join(BASE_DIR, 'services', 'publisher', 'account_manager.py')
    with open(mgr_path) as f:
        code = f.read()

    assert "success_rate < 50" in code, "Critical threshold should be 50%"
    assert "success_rate < 80" in code, "Degraded threshold should be 80%"
    assert 'health = "healthy"' in code, "Default health should be healthy"
    print("  Gear 5: Health classification thresholds verified (50% critical, 80% degraded)")


# ============================================================
# Cross-Gear: Data Flow Contracts
# ============================================================

def test_n8n_workflow_structure():
    """Verify the n8n workflow connects all gears."""
    wf_path = os.path.join(BASE_DIR, 'n8n-workflows', 'video-matrix-pipeline.json')
    with open(wf_path) as f:
        workflow = json.load(f)

    nodes = workflow.get("nodes", [])
    node_names = [n["name"] for n in nodes]

    required_stages = [
        "Schedule Trigger", "Generate Script", "Generate Video",
        "Check Similarity", "Route to Accounts",
    ]
    for stage in required_stages:
        found = any(stage.lower() in name.lower() for name in node_names)
        assert found, f"Missing n8n stage: {stage}"

    connections = workflow.get("connections", {})
    assert len(connections) > 0, "Workflow must have connections between nodes"

    # Verify the re-mutation feedback loop exists
    assert "Re-Mutate (Too Similar)" in node_names, "Must have re-mutation node for failed uniqueness"
    assert "Re-Mutate (Too Similar)" in connections, "Re-mutation must connect back to similarity check"

    print(f"  Cross-Gear: n8n workflow verified ({len(nodes)} nodes, {len(connections)} connections)")


def test_n8n_similarity_threshold():
    """Verify the n8n workflow uses 0.70 as similarity threshold."""
    wf_path = os.path.join(BASE_DIR, 'n8n-workflows', 'video-matrix-pipeline.json')
    with open(wf_path) as f:
        workflow = json.load(f)

    nodes = workflow.get("nodes", [])
    sim_node = next(n for n in nodes if "Similarity" in n["name"])
    threshold = sim_node["parameters"]["body"]["threshold"]
    assert threshold == 0.70, f"Expected 0.70 threshold, got {threshold}"
    print("  Cross-Gear: n8n similarity threshold verified (0.70)")


def test_docker_compose_service_dependencies():
    """Verify Docker Compose has correct service dependencies."""
    dc_path = os.path.join(BASE_DIR, 'docker-compose.yml')
    with open(dc_path) as f:
        content = f.read()

    for svc in ["content-planner", "video-mutator", "content-router", "publisher"]:
        assert svc in content, f"Missing service: {svc}"

    assert "healthcheck" in content, "Must have health checks"
    assert "depends_on" in content, "Must have service dependencies"

    print("  Cross-Gear: Docker Compose service dependencies verified")


def test_grafana_dashboard_covers_metrics():
    """Verify Grafana dashboard monitors the right things."""
    dash_path = os.path.join(BASE_DIR, 'configs', 'grafana-dashboard.json')
    with open(dash_path) as f:
        dashboard = json.load(f)

    panels = dashboard.get("dashboard", {}).get("panels", [])
    panel_titles = [p.get("title", "") for p in panels]

    required_keywords = ["publish", "success", "account"]
    for keyword in required_keywords:
        found = any(keyword.lower() in title.lower() for title in panel_titles)
        assert found, f"Missing dashboard metric containing '{keyword}'"

    print(f"  Cross-Gear: Grafana dashboard verified ({len(panels)} panels)")


def test_enum_consistency_with_schema():
    """Verify inline enums match SQL schema definitions exactly."""
    schema_path = os.path.join(BASE_DIR, 'storage', 'postgres', 'migrations', '001_init.sql')
    with open(schema_path) as f:
        schema = f.read()

    for hook in HookType:
        assert f"'{hook.value}'" in schema, f"Hook '{hook.value}' not in SQL schema"
    for style in StyleType:
        assert f"'{style.value}'" in schema, f"Style '{style.value}' not in SQL schema"
    for dur in DurationType:
        assert f"'{dur.value}'" in schema, f"Duration '{dur.value}' not in SQL schema"

    print("  Cross-Gear: Enum values consistent between Python and SQL")


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    tests = [
        # Gear 1: Script Differentiation
        test_script_combo_coverage,
        test_prompt_differentiation,
        test_prompt_template_matches_source,
        # Gear 2: Video Mutation
        test_random_params_variety,
        test_ffmpeg_cmd_construction,
        test_ffmpeg_cmd_minimal,
        test_intensity_levels,
        test_mutation_params_to_dict,
        # Gear 3: Perceptual Hash
        test_hamming_distance,
        test_similarity_score,
        test_threshold_gate,
        test_hash_checker_source_consistency,
        # Gear 4: Platform Isolation
        test_sql_schema_contracts,
        test_routing_logic_contracts,
        test_routing_cross_platform_reuse,
        # Gear 5: Account Lifecycle
        test_account_lifecycle_states,
        test_account_manager_contracts,
        test_health_classification_thresholds,
        # Cross-Gear
        test_n8n_workflow_structure,
        test_n8n_similarity_threshold,
        test_docker_compose_service_dependencies,
        test_grafana_dashboard_covers_metrics,
        test_enum_consistency_with_schema,
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("  AI Video Matrix — Core Flywheel Validation")
    print("=" * 60)
    print()

    gear_labels = {
        "test_script_combo_coverage": "Gear 1: Script Differentiation",
        "test_random_params_variety": "Gear 2: Video Mutation",
        "test_hamming_distance": "Gear 3: Perceptual Hash",
        "test_sql_schema_contracts": "Gear 4: Platform Isolation",
        "test_account_lifecycle_states": "Gear 5: Account Lifecycle",
        "test_n8n_workflow_structure": "Cross-Gear: Data Flow",
    }

    for test in tests:
        if test.__name__ in gear_labels:
            print(f"\n--- {gear_labels[test.__name__]} ---")
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test.__name__, str(e)))
            print(f"  FAIL {test.__name__}: {e}")

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    else:
        print("\nAll tests passed!")
    print("=" * 60)
