"""Fine-tune Llama 3.2 3B Instruct on mental-health counseling + screening behavior.

Uses QLoRA (4-bit quantization + LoRA adapters) for memory-efficient training.
Requires a CUDA GPU with at least 16 GB VRAM.

Usage:
    python -m ml_ai.prompts.finetuning
    python -m ml_ai.prompts.finetuning --epochs 3 --max-samples 500
    python -m ml_ai.prompts.finetuning --output-dir ./my_model
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
DEFAULT_OUTPUT_DIR = str(Path(__file__).parent / "llama-3.2-3b-mental-health-screening")


def check_gpu():
    import torch
    if not torch.cuda.is_available():
        print("ERROR: No CUDA GPU detected. Fine-tuning requires a GPU.")
        sys.exit(1)
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"GPU detected: {gpu_name} ({vram:.1f} GB VRAM)")
    if vram < 14:
        print(f"WARNING: {vram:.1f} GB may be too low. Recommended: 16+ GB.")
    return torch.cuda.is_bf16_supported()


def login_hf():
    from huggingface_hub import login

    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN is not set. Set it in the environment instead of hard-coding "
            "a Hugging Face token in source code."
        )
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face Hub.")


def load_model_and_tokenizer():
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import torch

    print(f"Downloading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    compute_dtype = torch.bfloat16
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        dtype=compute_dtype,
    )
    print(f"Model loaded: {MODEL_NAME} (4-bit QLoRA)")
    return model, tokenizer


def apply_lora(model, r: int = 16, lora_alpha: int = 32, lora_dropout: float = 0.05):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType

    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    model = get_peft_model(model, peft_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"LoRA applied: {trainable:,} trainable / {total:,} total ({100 * trainable / total:.2f}%)")
    return model


def load_and_format_dataset(
    tokenizer,
    max_samples: int | None = None,
    dataset_path: str | None = None,
):
    from datasets import load_dataset

    data_path = dataset_path or str(
        Path(__file__).parent / "train_translated_converted.jsonl"
    )
    print(f"Loading dataset: {data_path}...")
    ds = load_dataset("json", data_files=data_path, split="train")
    print(f"Dataset loaded: {len(ds)} samples")

    if max_samples and max_samples < len(ds):
        ds = ds.shuffle(seed=42).select(range(max_samples))
        print(f"Dataset subsampled to {max_samples}")

    def format_example(example):
        user_msg = example.get("input", "")
        assistant_msg = example.get("output", "")
        system_msg = example.get("system", "")
        if not user_msg or not assistant_msg:
            return {"text": ""}
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
        return {
            "text": tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        }

    ds = ds.map(format_example, remove_columns=ds.column_names)
    ds = ds.filter(lambda x: len(x["text"]) > 0)
    ds = ds.shuffle(seed=3407)

    print(f"Final training set: {len(ds)} samples")
    print("Dataset formatted with Llama 3.2 chat template.")
    return ds


def train(model, tokenizer, dataset, args):
    import gc
    import torch
    from trl import SFTTrainer, SFTConfig

    torch.cuda.empty_cache()
    gc.collect()

    sft_config = SFTConfig(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        warmup_steps=10,
        report_to="none",
        seed=3407,
        max_grad_norm=0.3,
        dataset_text_field="text",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
        args=sft_config,
    )

    print("Starting training...")
    trainer.train()
    print("Training complete.")
    return trainer


def save_model(trainer, tokenizer, output_dir: str):
    print(f"Saving model to {output_dir}...")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model saved to {output_dir}")
    print(f"Files: {os.listdir(output_dir)}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Llama 3.2 3B Instruct")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit samples for quick testing")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).parent / "train_translated_converted.jsonl"),
        help="Path to training JSONL dataset",
    )
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    args = parser.parse_args()

    supports_bf16 = check_gpu()
    if not supports_bf16:
        print("WARNING: GPU does not support bfloat16. Training may be slower.")

    login_hf()
    model, tokenizer = load_model_and_tokenizer()
    model = apply_lora(model, r=args.r, lora_alpha=args.lora_alpha)
    dataset = load_and_format_dataset(
        tokenizer,
        max_samples=args.max_samples,
        dataset_path=args.dataset,
    )
    trainer = train(model, tokenizer, dataset, args)
    save_model(trainer, tokenizer, args.output_dir)
    print("\nDone! Model is ready for inference.")


if __name__ == "__main__":
    main()
