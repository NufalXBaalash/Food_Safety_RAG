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


def convert_to_markdown(input_file_path: Path, output_folder: Path) -> Path:
    """
    Converts a PDF, DOC, or DOCX file to Markdown using Docling.
    Features Smart OCR:
      1. Tries to extract text natively (do_ocr=False) which finishes in seconds.
      2. If extracted text is minuscule (< 100 words), assumes it's a scanned 
         image and falls back to heavy OCR (do_ocr=True).
      3. Enforces a strict 5 minute timeout on extraction.
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / f"{input_file_path.stem}.md"

    # 1. Attempt Native PyMuPDF Text Reading (Blindingly Fast)
    log.info(f"    ↳ Attempting native reading (OCR disabled)...")
    text_content = _convert_with_timeout(input_file_path, do_ocr=False, timeout_sec=120)
    
    word_count = len(text_content.split())
    if word_count < 100:
        log.warning(f"    ↳ Extracted only {word_count} words natively. File is likely an image scan. Retrying with Heavy OCR...")
        text_content = _convert_with_timeout(input_file_path, do_ocr=True, timeout_sec=300)

    output_path.write_text(text_content, encoding="utf-8")
    return output_path
