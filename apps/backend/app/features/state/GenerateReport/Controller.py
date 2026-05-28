from .Handler import GenerateReportHandler
from shared.logger import logging_func
logger = logging_func(__name__)


def generate_report(data_dir: str = "data", paper: bool = False) -> str:
    handler = GenerateReportHandler(data_dir=data_dir, paper=paper)
    return handler.generate_report()


def generate_report_structured(data_dir: str = "data", paper: bool = False) -> dict:
    from .Schema import TradeReport
    handler = GenerateReportHandler(data_dir=data_dir, paper=paper)
    report: TradeReport = handler.generate_structured()
    return report.model_dump()
