"""Merge LoRA adapter with base model and save full fine-tuned model."""
from __future__ import annotations

import os
import json
from pathlib import Path

HF_TOKEN = "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"
BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
ADAPTER_DIR = str(Path(__file__).parent / "llama-3.2-3b-mental-health-screening")
OUTPUT_DIR = str(Path(__file__).parent.parent.parent / "saved" / "llama-3.2-3b-mental-health-merged")


def main():
    print(f"Base model: {BASE_MODEL}")
    print(f"Adapter: {ADAPTER_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    from huggingface_hub import login
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face Hub.")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
    from peft import PeftModel
    from safetensors.torch import save_file

    print("Loading base model (float16)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="cpu",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR, trust_remote_code=True)
    config = AutoConfig.from_pretrained(BASE_MODEL, trust_remote_code=True)
    print("Base model loaded.")

    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    print("Adapter loaded.")

    print("Merging adapter into base model...")
    model = model.merge_and_unload()
    print("Merge complete.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    state_dict = model.state_dict()
    total_params = len(state_dict)
    print(f"Total parameters: {total_params}")

    # Save as single model.safetensors
    print("Saving model.safetensors (single file)...")
    cpu_sd = {}
    seen = set()
    for k, v in state_dict.items():
        v_cpu = v.cpu().contiguous()
        v_data_ptr = v_cpu.data_ptr()
        if v_data_ptr in seen:
            # Clone tied weight to avoid safetensors shared memory error
            v_cpu = v_cpu.clone()
        else:
            seen.add(v_data_ptr)
        cpu_sd[k] = v_cpu
    save_file(cpu_sd, os.path.join(OUTPUT_DIR, "model.safetensors"))
    print("model.safetensors saved.")

    # Save config without quantization_config
    config_dict = config.to_dict()
    config_dict.pop("quantization_config", None)
    # Add torch_dtype for proper loading
    config_dict["torch_dtype"] = "float16"
    config_path = os.path.join(OUTPUT_DIR, "config.json")
    with open(config_path, "w") as f:
        json.dump(config_dict, f, indent=2)
    print("Saved config.json")

    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"Model saved. Files: {os.listdir(OUTPUT_DIR)}")
    print("Done!")


if __name__ == "__main__":
    main()
