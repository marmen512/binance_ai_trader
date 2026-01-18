"""
OFFLINE FINETUNING CORE (CPU ONLY)

CRITICAL:
- Offline only
- No live / paper / CI imports allowed
- Manual execution only
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)

from core.logging import setup_logger

logger = setup_logger("offline_finetuning_core")


class InstructionDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_len: int = 512):
        self.samples = []
        self.tokenizer = tokenizer
        self.max_len = max_len

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                text = obj["instruction"] + "\n\n" + obj["response"]
                self.samples.append(text)

        logger.info(f"Loaded {len(self.samples)} instruction samples")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.samples[idx],
            truncation=True,
            max_length=self.max_len,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": enc["input_ids"].squeeze(0),
        }


def fine_tune_pass(
    *,
    dataset_path: str | Path,
    model_name: str,
    output_dir: str | Path,
    learning_rate: float,
    num_epochs: int,
    batch_size: int,
):
    logger.warning("OFFLINE TRAINING STARTED (MANUAL MODE)")

    dataset_path = Path(dataset_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cpu")
    logger.info("Device: CPU")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.to(device)
    model.train()

    dataset = InstructionDataset(dataset_path, tokenizer)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = AdamW(model.parameters(), lr=learning_rate)

    for epoch in range(1, num_epochs + 1):
        logger.info(f"Epoch {epoch}/{num_epochs}")
        total_loss = 0.0

        for step, batch in enumerate(loader, start=1):
            optimizer.zero_grad()
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch)
            loss = out.loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg = total_loss / max(len(loader), 1)
        logger.info(f"Epoch {epoch} avg loss={avg:.4f}")

    logger.info("Saving model")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    logger.warning("OFFLINE TRAINING FINISHED")
