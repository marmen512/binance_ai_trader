"""
OFFLINE FINETUNING CORE — REAL TRAINING (MINIMAL)

WARNING:
- MANUAL EXECUTION ONLY
- NO PAPER / LIVE / CI USAGE
- RUN ONLY AFTER PAPER-v1 FREEZE
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from core.logging import setup_logger

logger = setup_logger("binance_ai_trader.offline_finetuning_core")


def fine_tune_pass(
    *,
    dataset_path: str,
    model_name: str,
    output_dir: str | Path,
    batch_size: int = 2,
    learning_rate: float = 5e-6,
    num_epochs: int = 1,
    early_stopping_patience: int | None = None,
    save_total_limit: int = 2,
) -> dict[str, Any]:
    """
    Execute a single offline fine-tuning pass.

    This function performs REAL model training.
    It must NEVER be called automatically.
    """

    logger.warning("⚠ REAL OFFLINE TRAINING STARTED")

    dataset_path = Path(dataset_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        raise FileNotFoundError(dataset_path)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # -------------------------
    # Load instruction dataset
    # -------------------------
    texts: list[str] = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)

            response = (
                obj.get("response")
                or obj.get("output")
                or ""
            )

            text = (
                f"Instruction: {obj['instruction']}\n"
                f"Response: {response}"
            )

            texts.append(text)

    if not texts:
        raise RuntimeError("Dataset is empty — aborting offline training")

    encodings = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=512,
        return_tensors="pt",
    )

    class SimpleDataset(torch.utils.data.Dataset):
        def __init__(self, enc):
            self.enc = enc

        def __len__(self):
            return self.enc["input_ids"].size(0)

        def __getitem__(self, idx):
            return {k: v[idx] for k, v in self.enc.items()}

    dataset = SimpleDataset(encodings)

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        overwrite_output_dir=True,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        save_total_limit=save_total_limit,
        save_strategy="no",   # контроль збереження ВРУЧНУ
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
        optimizers=(AdamW(model.parameters(), lr=learning_rate), None),
    )

    # -------------------------
    # REAL TRAINING
    # -------------------------
    trainer.train()

    # -------------------------
    # FORCE SAVE (CRITICAL)
    # -------------------------
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # -------------------------
    # Save training metadata
    # -------------------------
    meta = {
        "mode": "offline-training",
        "dataset": str(dataset_path),
        "model_name": model_name,
        "epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
    }

    with open(output_dir / "training_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("✅ OFFLINE TRAINING FINISHED")

    return {
        "status": "ok",
        "output_dir": str(output_dir),
    }
