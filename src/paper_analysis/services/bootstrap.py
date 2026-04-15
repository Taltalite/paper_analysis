from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.adapters.parser.plain_text import PlainTextParser
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.runtime.crewai_runtime import CrewAIRuntime
from paper_analysis.runtime.crews.base import CrewAITwoAgentTextAnalysisRunner
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline
from paper_analysis.services.analysis_service import AnalysisService
from paper_analysis.services.artifact_service import ArtifactService


def build_default_analysis_service() -> AnalysisService:
    llm_client = create_llm_client_from_env()
    crew_runner = CrewAITwoAgentTextAnalysisRunner(llm_client=llm_client, verbose=True)
    runtime = CrewAIRuntime(
        general_text_pipeline=GeneralTextPipeline(crew_runner=crew_runner),
        research_paper_pipeline=ResearchPaperPipeline(crew_runner=crew_runner),
    )
    return AnalysisService(
        text_parser=PlainTextParser(),
        pdf_parser=PdfParser(),
        runtime=runtime,
    )


def build_default_artifact_service() -> ArtifactService:
    return ArtifactService(storage=LocalFilesystemArtifactStorage())
