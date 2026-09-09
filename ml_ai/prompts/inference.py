from __future__ import annotations

from threading import Thread

import torch
from pathlib import Path
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)
from peft import PeftModel

BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
ADAPTER_DIR = str(Path(__file__).parent / "llama-3.2-3b-mental-health-screening")

_model = None
_tokenizer = None


def load_model():
    """Load the fine-tuned Llama once during application startup."""
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    print("Loading fine-tuned LLM...")

    compute_dtype = torch.bfloat16

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    _tokenizer = AutoTokenizer.from_pretrained(
        ADAPTER_DIR,
        trust_remote_code=True,
    )

    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        dtype=compute_dtype,
    )

    _model = PeftModel.from_pretrained(base, ADAPTER_DIR)
    _model.eval()

    print("Fine-tuned LLM loaded.")

    return _model, _tokenizer


def preload():
    """Load the fine-tuned LLM into memory at startup."""
    load_model()


def warmup_model():
    """Trigger CUDA/model initialization before the first real chat request."""
    model, tokenizer = load_model()

    messages = [
        {"role": "user", "content": "Hello."},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.inference_mode():
        model.generate(
            **inputs,
            max_new_tokens=1,
            do_sample=False,
        )

    print("LLM warmup complete.")


def generate(
    messages: list[dict],
    max_new_tokens: int = 256,
    temperature: float = 0.7,
) -> str:
    model, tokenizer = load_model()

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
        )

    generated = output[0][inputs["input_ids"].shape[1]:]

    return tokenizer.decode(
        generated,
        skip_special_tokens=True,
    ).strip()


def generate_stream(
    messages: list[dict],
    max_new_tokens: int = 256,
    temperature: float = 0.7,
):
    model, tokenizer = load_model()

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    generation_kwargs = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "do_sample": True,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
        "streamer": streamer,
    }

    thread = Thread(
        target=model.generate,
        kwargs=generation_kwargs,
    )
    thread.start()

    try:
        for chunk in streamer:
            yield chunk
    finally:
        thread.join()
