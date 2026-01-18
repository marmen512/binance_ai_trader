import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "checkpoints/offline_pass_1_dry"

PROMPTS = [
    "Instruction: Explain what overfitting is.\nResponse:",
    "Instruction: Give one risk of high leverage trading.\nResponse:",
    "Instruction: What is a stop-loss?\nResponse:",
]

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)

model.eval()

for i, prompt in enumerate(PROMPTS, 1):
    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
        )

    text = tokenizer.decode(output[0], skip_special_tokens=True)

    print("=" * 80)
    print(f"[TEST {i}]")
    print(text)
