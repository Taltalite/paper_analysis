"""同文档顺序追问；历史只辅助定位，不能替代原始证据。"""
from __future__ import annotations

import fcntl
import re
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.execution import ResolvedPolicy
from paper_analysis.domain.qa import QuestionJob, QuestionRequest


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_sha256: str
    source_question_id: UUID
    policy: ResolvedPolicy
    turns: list[UUID] = Field(default_factory=list)


class ConversationService:
    def __init__(self, service) -> None:
        self.service = service
        self.root = service.root / "conversations"

    def directory(self, identifier: UUID) -> Path:
        return self.root / str(identifier)

    def get(self, identifier: UUID) -> Conversation:
        return Conversation.model_validate_json((self.directory(identifier) / "conversation.json").read_text())

    def create(self, identifier: UUID) -> Conversation:
        directory = self.service.store.directory(identifier)
        self.service.store.get(identifier)
        with (directory / "conversation.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self._create_locked(identifier)

    def _create_locked(self, identifier: UUID) -> Conversation:
        job = self.service.store.get(identifier)
        if job.conversation_id:
            return self.get(job.conversation_id)
        if job.status != "completed":
            raise ValueError("请先等待首轮问答完成。")
        result = Conversation(document_sha256=job.document_sha256, source_question_id=job.id,
            policy=job.policy or ResolvedPolicy.resolve(job.request.execution_policy_request()), turns=[job.id])
        directory = self.directory(result.id)
        directory.mkdir(parents=True)
        budget = self.service.store.directory(job.id) / "budget.json"
        if budget.exists():
            shutil.copyfile(budget, directory / "budget.json")
        atomic_json(directory / "conversation.json", result)
        job.conversation_id = result.id
        self.service.store.save(job)
        return result

    def prepare_turn(self, identifier: UUID, request: QuestionRequest) -> QuestionJob:
        directory = self.directory(identifier)
        # get 在 open 前检查存在性，UUID 路径不接受任意本地文件。
        self.get(identifier)
        with (directory / "turn.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            conversation = self.get(identifier)
            previous = self.service.store.get(conversation.turns[-1])
            if previous.status in {"queued", "running"}:
                raise ValueError("上一轮仍在执行，请等待或取消后再追问。")
            if re.search(r"它|这张图|上一张图|该图", request.question) and not request.figure:
                if not previous.request.figure:
                    raise ValueError("无法唯一确定指代，请明确图号或研究对象。")
                request = request.model_copy(update={"figure": previous.request.figure, "panel": previous.request.panel})
            policy = ResolvedPolicy.resolve(request.execution_policy_request(), server_limits=conversation.policy.effective)
            source = self.service.store.directory(conversation.source_question_id) / "source.pdf"
            source_job = self.service.store.get(conversation.source_question_id)
            import hashlib
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != conversation.document_sha256:
                raise ValueError("会话文档指纹不匹配。")
            job = self.service.prepare(filename=source_job.filename, content=content, request=request)
            job.conversation_id = identifier
            job.parent_turn_id = previous.id
            job.policy = policy
            self.service.store.save(job)
            conversation.turns.append(job.id)
            atomic_json(directory / "conversation.json", conversation)
            return job
