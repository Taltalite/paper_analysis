"""两次合成输入真实接口冒烟；无论文外发，无自动重试。"""
import json
import time
import sys
from pathlib import Path

from paper_analysis.env import load_project_dotenv
from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.runtime.budget import BudgetLedger
from scripts.verify_vision import make_visual_fixture

ROOT = Path(__file__).parent
load_project_dotenv()
client = create_llm_client_from_env()
results = json.loads(ROOT.joinpath("live-smoke.json").read_text()) if "--text-only" in sys.argv else []
def save():
    ROOT.joinpath("live-smoke.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))

started = time.monotonic()
try:
    llm = client.to_crewai_llm()
    llm.max_tokens = 1024
    llm.max_retries = 0
    llm.timeout = 45
    llm._client.max_retries = 0
    llm._client.timeout = 45
    answer = llm.call("这是合成接口测试：研究用了3个生物学重复，每个重复测量2次。请只回答生物学重复数和技术测量总数，用一句中文。")
    text = str(answer)
    results.append({"case": "kimi_synthetic_text", "model": client.audit_metadata()["model"],
        "passed": "3" in text and "6" in text, "response": text,
        "usage": llm.get_token_usage_summary().model_dump(),
        "elapsed_seconds": round(time.monotonic()-started,3),
        "scope": "适配器返回的 CrewAI LLM；手动设置测试输出/超时/重试限额，不代表生产策略已传递"})
except Exception as exc:
    results.append({"case": "kimi_synthetic_text", "passed": False, "error_type": type(exc).__name__})
save()
if "--text-only" in sys.argv:
    print(json.dumps({"case": results[-1]["case"], "passed": results[-1]["passed"],
                      "error_type": results[-1].get("error_type")}))
    raise SystemExit(0)

started = time.monotonic()
policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(token_budget=10000, max_calls=1, max_output_tokens=1024))
ledger = BudgetLedger(job_id="synthetic-vision-smoke", attempt=1, policy=policy.effective)
try:
    fixture = make_visual_fixture(ROOT / "images")
    client._request_timeout = 45
    text = client.complete_with_images(prompt="请用简体中文列出图中两根柱子的英文名称与标注数值，不补充推断。",
        image_paths=[Path(fixture.figures[0].image_block_paths[0])],
        execution_context=ledger, max_output_tokens=1024)
    results.append({"case": "qwen_synthetic_image", "model": client.vision_model,
        "passed": all(x in text for x in ("Alpha","Beta","37","83")), "response": text,
        "execution": ledger.summary().model_dump(mode="json"),
        "elapsed_seconds": round(time.monotonic()-started,3)})
except Exception as exc:
    results.append({"case": "qwen_synthetic_image", "passed": False, "error_type": type(exc).__name__,
        "execution": ledger.summary(stop_reason="provider_error").model_dump(mode="json")})
save()
print(json.dumps([{"case": x["case"], "passed": x["passed"], "error_type": x.get("error_type")} for x in results]))
