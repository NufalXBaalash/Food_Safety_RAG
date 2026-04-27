import multiprocessing
from pathlib import Path
from config.settings import settings
import logging

log = logging.getLogger(__name__)

def _run_conversion_worker(input_file_str: str, do_ocr: bool, device_str: str, result_queue):
    """
    Isolated worker process for Docling conversion. This prevents PyTorch VRAM leakage
    and allows hard-killing the process if it exceeds the 5 minute strict timeout.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    import traceback
    
    try:
        device_map = {
            "cpu":  AcceleratorDevice.CPU,
            "cuda": AcceleratorDevice.CUDA,
            "mps":  AcceleratorDevice.MPS,
            "xpu":  AcceleratorDevice.XPU,
            "auto": AcceleratorDevice.AUTO,
        }
        device = device_map.get(device_str, AcceleratorDevice.CPU)

        pdf_pipeline_options = PdfPipelineOptions(
            do_ocr=do_ocr,
            do_table_structure=True,
            table_structure_options=TableStructureOptions(do_cell_matching=True),
            accelerator_options=AcceleratorOptions(
                num_threads=4,
                device=device,
            ),
        )

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options)
            }
        )

        converted_doc = converter.convert(input_file_str)
        text_content = converted_doc.document.export_to_markdown()
        result_queue.put({"status": "success", "text": text_content})
    except Exception as e:
        result_queue.put({"status": "error", "message": traceback.format_exc()})


def _convert_with_timeout(input_file_path: Path, do_ocr: bool, timeout_sec: int) -> str:
    import queue
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    p = ctx.Process(
        target=_run_conversion_worker, 
        args=(str(input_file_path), do_ocr, settings.ACCELERATOR_DEVICE, result_queue)
    )
    p.start()

    try:
        # We must pull from the queue BEFORE joining to prevent pipe deadlocks
        # when the worker returns a large string!
        res = result_queue.get(timeout=timeout_sec)
        p.join(5)
    except queue.Empty:
        p.terminate()
        p.join()
        raise TimeoutError(f"Docling conversion exceeded the strict {timeout_sec} seconds timeout.")

    if res["status"] == "success":
        return res["text"]
    else:
        raise RuntimeError(f"Worker Error: {res['message']}")


import re

def clean_markdown_text(text: str) -> str:
    # Remove common repetitive footers and headers (Arabic variants)
    # E.g., "الهيئة العامة للغذاء والدواء ص x"
    text = re.sub(r'الهيئة العامة للغذاء والدواء.*?\d+', '', text)
    # Remove standalone page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Condense multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def convert_to_markdown(input_file_path: Path, output_folder: Path) -> Path:
    """
    Converts a PDF, DOC, or DOCX file to Markdown using Docling.
    OCR is permanently disabled — only native text extraction is used.
    Enforces a strict 2 minute timeout on extraction.
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / f"{input_file_path.stem}.md"

    # 1. Attempt Native Text Reading (OCR disabled)
    log.info(f"    ↳ Attempting native reading (OCR disabled)...")
    text_content = _convert_with_timeout(input_file_path, do_ocr=False, timeout_sec=120)

    # Clean the extracted text before saving
    text_content = clean_markdown_text(text_content)

    output_path.write_text(text_content, encoding="utf-8")
    return output_path
