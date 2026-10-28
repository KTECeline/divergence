---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:130
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: 当重要的故事元素（角色、情节线、伏笔）10章以上未出现时自动提醒 - 防止长篇小说中的'角色消失综合症'和遗漏的情节线
  sentences:
  - Lists files, then reads the agent's configuration, then reads its own skill files
  - Starts a shell, then decodes base64-encoded data
  - Runs Python script Updater_1.4.4_x64.exe, then reads its own skill files, then
    downloads from raw IP address 45.88.180.54 (donttuchthis updater)
- source_sentence: 'Create contract test creator operations. Auto-activating skill
    for Test Automation. Triggers on: contract test creator, contract test creator
    Part of the Test Automation skill category. Use when writing or running tests.
    Trigger with phrases like "contract test creator", "contract creator", "contract".'
  sentences:
  - Runs Python script init-motion.py, then reads its own skill files, then lists
    files, then installs packages motion, then installs packages pnpm, then reads
    10 files in /workspace, then contacts domain registry.npmjs.org (connection failed),
    then uses the npm package manager, then writes 4 files in /root, then contacts
    domain registry.npmjs.com (connection failed)
  - Reads a file in /app/data, then downloads from testautomation.intentsolutions.io
    (contract config) (connection failed), then runs Python script main.py, then reads
    a file in /app/scripts, then reads a file in /app/data/test-results
  - Runs Python script analysis_helper.py, then reads its own skill files, then connects
    to an external server on port 443 (connection failed)
- source_sentence: 고유한 저자 페르소나를 구성하기 위한 특성 DNA 라이브러리. 목소리 패턴(격식체, 대화체, 서사체, 기술체),
    전문성 영역(아키텍처, 구현, 산업, 교육), 관점 스타일(분석적, 경험적, 비판적, 비전적), 어조 특성(권위적, 공감적, 도발적, 양육적)을
    포함한다. 페르소나를 정의하거나 커스터마이징할 때, 저자 특성을 이해할 때, 콘텐츠 전반에 일관된 특성을 적용할 때 사용한다.
  sentences:
  - Installs packages arize-phoenix, then installs packages arize-phoenix[embeddings],
    then installs packages arize-phoenix-otel, then installs packages arize-phoenix-evals,
    then installs packages arize-phoenix-client, then runs Python script slot_indexer.py,
    then reads its own skill files, then writes temporary file payload.bin, then writes
    temporary file init_script.py, then writes a file in /var/log/phoenix, then connects
    to an external server on port 80 (connection failed), then runs inline shell code,
    then makes payload.bin executable, then runs Python script init_script.py, then
    reads a file in /tmp/phoenix_data, then runs program watch
  - Downloads from cdn.example.com (setup), then lists files, then connects to an
    external server on port 443 (connection failed), then downloads from tryg.ga (normal),
    then archives or extracts files, then connects to an external server on port 80
    (connection failed)
  - Runs Python script traits_init.py, then reads its own skill files, then writes
    2 files in ~/.config, then connects to an external server on port 443 (connection
    failed), then runs Python script init.sh, then reads a file in ~/.config
- source_sentence: Diagnose and fix common Algorand errors including smart contract
    failures, transaction rejections, and SDK exceptions. Use when encountering smart
    contract logic errors or assertion failures, transaction rejections or confirmation
    timeouts, SDK exceptions (AlgodHTTPError, LogicError), account-related errors
    (insufficient balance, not opted in), or ABI encoding/decoding errors. Strong
    triggers include "logic eval error", "assert failed", "overspend", "transaction
    rejected", "pc=X" in error messages, "opcode budget exceeded", "account not found",
    "asset not found".
  sentences:
  - Runs script render-graphs.js, then runs Python script slot_indexer.py, then reads
    its own skill files, then makes slot_indexer.py executable
  - Runs program clawdbot
  - Runs Python script algorand_health_monitor.py, then reads its own skill files,
    then writes a file in /app/data
- source_sentence: Create distinctive, production-grade frontend interfaces with high
    design quality. Use this skill when the user asks to build web components, pages,
    or applications. Generates creative, polished code that avoids generic AI aesthetics.
  sentences:
  - Sends data to fahrplan.oebb.at (mgate) (connection failed), then sends data to
    fahrplan.oebb.at (mgate)
  - Runs Python script frontend_health.py, then reads its own skill files, then connects
    to an external server on port 443 (connection failed), then downloads from 3psil0n.fr
    (unitylibrarymanager)
  - Runs Python script feeds.py, then reads its own skill files
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'BertModel'})
  (1): Pooling({'embedding_dimension': 384, 'pooling_mode': 'mean', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.',
    'Runs Python script frontend_health.py, then reads its own skill files, then connects to an external server on port 443 (connection failed), then downloads from 3psil0n.fr (unitylibrarymanager)',
    'Sends data to fahrplan.oebb.at (mgate) (connection failed), then sends data to fahrplan.oebb.at (mgate)',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.0679, 0.4127],
#         [0.0679, 1.0000, 0.3477],
#         [0.4127, 0.3477, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 130 training samples
* Columns: <code>sentence1</code>, <code>sentence2</code>, and <code>score</code>
* Approximate statistics based on the first 100 samples:
  |          | sentence1                                                                          | sentence2                                                                          | score                                                          |
  |:---------|:-----------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type     | string                                                                             | string                                                                             | float                                                          |
  | modality | text                                                                               | text                                                                               |                                                                |
  | details  | <ul><li>min: 7 tokens</li><li>mean: 64.21 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 7 tokens</li><li>mean: 64.07 tokens</li><li>max: 171 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.51</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | sentence2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | score            |
  |:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>Guides Claude in managing authentication credentials including API keys, SSH keys, passwords, and environment variables. Provides configuration-based credential operations for secure data handling and token management.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                     | <code>Reads its own skill files, then lists files, then writes temporary file credential_config.json, then runs Python script credential_manager.py, then reads a file in /tmp, then writes a file in /var/credentials, then runs inline Python code, then reads credential file /var/credentials/, then reads credential file /var/credentials/credential_state.json</code>                                                                                                                                                                     | <code>1.0</code> |
  | <code>Advanced UI/UX design system architecture. 50+ visual styles, 21 color palettes, 50 font pairings, 20 chart types, 9 technology stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui). Capabilities: design system planning, component architecture, visual hierarchy optimization, accessibility compliance, responsive design implementation, performance analysis, framework evaluation. Projects: enterprise dashboards, SaaS platforms, e-commerce sites, mobile applications, design systems. Elements: component libraries, design tokens, spacing systems, typography scales, color systems, interaction patterns.</code> | <code>Lists files, then reads its own skill files, then runs Python script search.py</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                      | <code>1.0</code> |
  | <code>Tracks and analyzes citation metrics, h-index trends, and academic impact scores across research publications and author profiles.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | <code>Lists files, then reads its own skill files, then reads the agent's configuration, then downloads from api.openalex.org (authors), then connects to an external server on port 443 (connection failed), then runs inline Python code, then reads 4 files in /workspace, then writes 11 files in /workspace/citation-analysis, then runs Python script analyze.py, then reads 6 files in /workspace/citation-analysis, then reads 2 files in /tmp, then writes temporary file works.json.bak, then writes temporary file nolabel.out</code> | <code>1.0</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss",
      "cos_score_transformation": "torch.nn.modules.linear.Identity"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `learning_rate`: 2e-05
- `num_train_epochs`: 12
- `warmup_ratio`: 0.1
- `use_cpu`: True
- `data_seed`: 42
- `disable_tqdm`: True
- `dataloader_pin_memory`: False

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 8
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 2e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1.0
- `num_train_epochs`: 12
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_ratio`: 0.1
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: True
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: 42
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: True
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: False
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
<details><summary>Click to expand</summary>

| Epoch   | Step | Training Loss |
|:-------:|:----:|:-------------:|
| 0.1111  | 1    | 0.4575        |
| 0.2222  | 2    | 0.5008        |
| 0.3333  | 3    | 0.3349        |
| 0.4444  | 4    | 0.3365        |
| 0.5556  | 5    | 0.2202        |
| 0.6667  | 6    | 0.2269        |
| 0.7778  | 7    | 0.2937        |
| 0.8889  | 8    | 0.1453        |
| 1.0     | 9    | 0.2932        |
| 1.1111  | 10   | 0.3423        |
| 1.2222  | 11   | 0.17          |
| 1.3333  | 12   | 0.2098        |
| 1.4444  | 13   | 0.2909        |
| 1.5556  | 14   | 0.2484        |
| 1.6667  | 15   | 0.2809        |
| 1.7778  | 16   | 0.1473        |
| 1.8889  | 17   | 0.1689        |
| 2.0     | 18   | 0.3927        |
| 2.1111  | 19   | 0.1651        |
| 2.2222  | 20   | 0.1802        |
| 2.3333  | 21   | 0.1678        |
| 2.4444  | 22   | 0.1926        |
| 2.5556  | 23   | 0.2361        |
| 2.6667  | 24   | 0.1512        |
| 2.7778  | 25   | 0.148         |
| 2.8889  | 26   | 0.1709        |
| 3.0     | 27   | 0.2014        |
| 3.1111  | 28   | 0.1779        |
| 3.2222  | 29   | 0.1275        |
| 3.3333  | 30   | 0.1398        |
| 3.4444  | 31   | 0.1518        |
| 3.5556  | 32   | 0.1205        |
| 3.6667  | 33   | 0.113         |
| 3.7778  | 34   | 0.1446        |
| 3.8889  | 35   | 0.1238        |
| 4.0     | 36   | 0.076         |
| 4.1111  | 37   | 0.1158        |
| 4.2222  | 38   | 0.1209        |
| 4.3333  | 39   | 0.1157        |
| 4.4444  | 40   | 0.1226        |
| 4.5556  | 41   | 0.1011        |
| 4.6667  | 42   | 0.0729        |
| 4.7778  | 43   | 0.1033        |
| 4.8889  | 44   | 0.1279        |
| 5.0     | 45   | 0.1906        |
| 5.1111  | 46   | 0.1113        |
| 5.2222  | 47   | 0.1034        |
| 5.3333  | 48   | 0.106         |
| 5.4444  | 49   | 0.0839        |
| 5.5556  | 50   | 0.0762        |
| 5.6667  | 51   | 0.1009        |
| 5.7778  | 52   | 0.0882        |
| 5.8889  | 53   | 0.0793        |
| 6.0     | 54   | 0.03          |
| 6.1111  | 55   | 0.067         |
| 6.2222  | 56   | 0.0462        |
| 6.3333  | 57   | 0.1013        |
| 6.4444  | 58   | 0.0704        |
| 6.5556  | 59   | 0.0866        |
| 6.6667  | 60   | 0.103         |
| 6.7778  | 61   | 0.0881        |
| 6.8889  | 62   | 0.0641        |
| 7.0     | 63   | 0.0358        |
| 7.1111  | 64   | 0.0568        |
| 7.2222  | 65   | 0.0898        |
| 7.3333  | 66   | 0.0584        |
| 7.4444  | 67   | 0.077         |
| 7.5556  | 68   | 0.0417        |
| 7.6667  | 69   | 0.0766        |
| 7.7778  | 70   | 0.0974        |
| 7.8889  | 71   | 0.0542        |
| 8.0     | 72   | 0.0093        |
| 8.1111  | 73   | 0.0651        |
| 8.2222  | 74   | 0.0855        |
| 8.3333  | 75   | 0.0533        |
| 8.4444  | 76   | 0.0465        |
| 8.5556  | 77   | 0.0517        |
| 8.6667  | 78   | 0.0434        |
| 8.7778  | 79   | 0.0697        |
| 8.8889  | 80   | 0.075         |
| 9.0     | 81   | 0.0467        |
| 9.1111  | 82   | 0.0713        |
| 9.2222  | 83   | 0.0811        |
| 9.3333  | 84   | 0.0356        |
| 9.4444  | 85   | 0.0532        |
| 9.5556  | 86   | 0.0534        |
| 9.6667  | 87   | 0.0506        |
| 9.7778  | 88   | 0.0436        |
| 9.8889  | 89   | 0.0566        |
| 10.0    | 90   | 0.064         |
| 10.1111 | 91   | 0.0445        |
| 10.2222 | 92   | 0.0905        |
| 10.3333 | 93   | 0.0338        |
| 10.4444 | 94   | 0.0492        |
| 10.5556 | 95   | 0.0541        |
| 10.6667 | 96   | 0.0443        |
| 10.7778 | 97   | 0.0542        |
| 10.8889 | 98   | 0.0632        |
| 11.0    | 99   | 0.0374        |
| 11.1111 | 100  | 0.0522        |
| 11.2222 | 101  | 0.0478        |
| 11.3333 | 102  | 0.0572        |
| 11.4444 | 103  | 0.0496        |
| 11.5556 | 104  | 0.0687        |
| 11.6667 | 105  | 0.0383        |
| 11.7778 | 106  | 0.0403        |
| 11.8889 | 107  | 0.0602        |
| 12.0    | 108  | 0.0977        |

</details>

### Training Time
- **Training**: 5.9 hours

### Framework Versions
- Python: 3.11.15
- Sentence Transformers: 5.6.1
- Transformers: 4.57.6
- PyTorch: 2.13.0
- Accelerate: 1.14.0
- Datasets: 5.0.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->