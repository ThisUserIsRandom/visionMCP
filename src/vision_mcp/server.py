"""The MCP server: wraps the vision pipeline as tools for a reasoning LLM."""

from fastmcp import FastMCP

from . import pipeline

PROMPTS = {
    "describe": "Describe this image in detail.",
    "ocr": "Transcribe all text in this image. If there is none, say so.",
    "compare": "Compare these two images and list the main similarities and differences.",
}


def build_server(cfg):
    server = FastMCP("visionMCP")

    def see(prompt, *images):
        return pipeline.look(cfg, list(images), prompt)

    @server.tool
    def describe_image(image: str) -> str:
        """Describe an image. `image` is a file path, URL, or data URI."""
        return see(PROMPTS["describe"], image)

    @server.tool
    def ask_about_image(image: str, question: str) -> str:
        """Answer a specific question about an image."""
        return see(question, image)

    @server.tool
    def extract_text(image: str) -> str:
        """Read all text in an image (OCR)."""
        return see(PROMPTS["ocr"], image)

    @server.tool
    def compare_images(image_a: str, image_b: str, question: str = "") -> str:
        """Compare two images. Optional `question` narrows the comparison."""
        return see(question or PROMPTS["compare"], image_a, image_b)

    @server.tool
    def server_status() -> dict:
        """Show the active provider, model, and transport."""
        return {
            "provider": cfg["provider"],
            "model": cfg["model"],
            "api_url": cfg["api_url"],
            "transport": cfg["transport"],
            "api_key_set": bool(cfg["api_key"]),
        }

    return server
