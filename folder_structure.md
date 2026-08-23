MENTAL_HEALTH_CARE/
│
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
│
├── clinical/
│   │
│   ├── documentation/
│   │   ├── conditions/
│   │   │   ├── depression.md
│   │   │   ├── anxiety.md
│   │   │   ├── bipolar_disorder.md
│   │   │   ├── schizophrenia.md
│   │   │   ├── ocd.md
│   │   │   ├── substance_use_disorder.md
│   │   │   ├── dementia.md
│   │   │   ├── autism_spectrum_disorder.md
│   │   │   └── adhd.md
│   │   │
│   │   ├── safety/
│   │   │   ├── critical_conditions.md
│   │   │   ├── self_harm_protocol.md
│   │   │   ├── crisis_identification.md
│   │   │   ├── escalation_protocol.md
│   │   │   └── safety_plan.md
│   │   │
│   │   ├── caregiver/
│   │   │   ├── caregiver_self_care.md
│   │   │   ├── caregiving_skills.md
│   │   │   ├── medication_management.md
│   │   │   └── rehabilitation.md
│   │   │
│   │   └── references/
│   │       ├── evidence_based_treatment.pdf
│   │       ├── intervention_guide.pdf
│   │       ├── mhgap.pdf
│   │       ├── psychology_intervention.pdf
│   │       └── selfhelp.pdf
│   │
│   ├── screening/
│   │   ├── phq9/
│   │   │   ├── PHQ-9_English.pdf
│   │   │   └── metadata.yaml
│   │   │
│   │   ├── phq4/
│   │   │   ├── PHQ-4.pdf
│   │   │   └── metadata.yaml
│   │   │
│   │   ├── gad7/
│   │   │   ├── GAD-7_English.pdf
│   │   │   └── metadata.yaml
│   │   │
│   │   ├── cssrs/
│   │   │   ├── C-SSRS-Full-Lifetime-Recent.pdf
│   │   │   └── metadata.yaml
│   │   │
│   │   └── safe_t/
│   │       ├── SAFE-T-Protocol-w-C-SSRS.pdf
│   │       └── metadata.yaml
│   │
│   └── clinical_registry/
│       ├── condition_registry.yaml
│       ├── screening_registry.yaml
│       ├── source_registry.yaml
│       └── safety_rules.yaml
│
├── data/
│   │
│   ├── raw/
│   │   ├── clinical_documents/
│   │   ├── screening_documents/
│   │   └── datasets/
│   │
│   ├── processed/
│   │   ├── documents/
│   │   ├── chunks/
│   │   ├── embeddings/
│   │   └── screening_data/
│   │
│   ├── external/
│   │   ├── huggingface/
│   │   ├── kaggle/
│   │   └── public_datasets/
│   │
│   └── README.md
│
├── ml_ai/
│   │
│   ├── rag/
│   │   ├── ingestion/
│   │   │   ├── pdf_loader.py
│   │   │   ├── document_cleaner.py
│   │   │   ├── chunker.py
│   │   │   └── metadata_extractor.py
│   │   │
│   │   ├── embeddings/
│   │   │   ├── embedding_model.py
│   │   │   └── embedding_config.yaml
│   │   │
│   │   ├── vectorstore/
│   │   │   ├── qdrant.py
│   │   │   └── pgvector.py
│   │   │
│   │   ├── retrieval/
│   │   │   ├── retriever.py
│   │   │   ├── reranker.py
│   │   │   └── filters.py
│   │   │
│   │   ├── generation/
│   │   │   ├── llm.py
│   │   │   ├── prompts.py
│   │   │   └── response_generator.py
│   │   │
│   │   └── pipelines/
│   │       └── rag_pipeline.py
│   │
│   ├── screening/
│   │   ├── scoring/
│   │   │   ├── phq9.py
│   │   │   ├── gad7.py
│   │   │   ├── phq4.py
│   │   │   └── cssrs.py
│   │   │
│   │   ├── interpretation/
│   │   │   ├── depression.py
│   │   │   ├── anxiety.py
│   │   │   └── safety.py
│   │   │
│   │   └── screening_engine.py
│   │
│   ├── safety/
│   │   ├── detection/
│   │   │   ├── keyword_rules.py
│   │   │   ├── classifier.py
│   │   │   └── intent_classifier.py
│   │   │
│   │   ├── risk/
│   │   │   ├── risk_features.py
│   │   │   ├── risk_engine.py
│   │   │   └── safety_overrides.py
│   │   │
│   │   ├── escalation/
│   │   │   ├── escalation_rules.py
│   │   │   └── routing.py
│   │   │
│   │   └── safety_pipeline.py
│   │
│   ├── longitudinal/
│   │   ├── baseline.py
│   │   ├── trend_detection.py
│   │   ├── change_detection.py
│   │   └── feature_engineering.py
│   │
│   ├── prediction/
│   │   ├── models/
│   │   │   ├── xgboost_model.py
│   │   │   ├── lightgbm_model.py
│   │   │   └── baseline_models.py
│   │   │
│   │   ├── training/
│   │   │   ├── train.py
│   │   │   ├── validation.py
│   │   │   └── hyperparameter_tuning.py
│   │   │
│   │   └── inference/
│   │       └── predictor.py
│   │
│   ├── evaluation/
│   │   ├── rag/
│   │   │   ├── retrieval_evaluation.py
│   │   │   └── answer_evaluation.py
│   │   │
│   │   ├── safety/
│   │   │   ├── safety_test_cases.yaml
│   │   │   ├── false_positive_analysis.py
│   │   │   └── false_negative_analysis.py
│   │   │
│   │   ├── screening/
│   │   │   └── scoring_validation.py
│   │   │
│   │   └── model_evaluation.py
│   │
│   ├── prompts/
│   │   ├── system_prompt.txt
│   │   ├── clinical_prompt.txt
│   │   ├── safety_prompt.txt
│   │   └── caregiver_prompt.txt
│   │
│   └── configs/
│       ├── model_config.yaml
│       ├── rag_config.yaml
│       └── safety_config.yaml
│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── assessments.py
│   │   │   ├── checkins.py
│   │   │   ├── medications.py
│   │   │   ├── caregivers.py
│   │   │   ├── safety.py
│   │   │   ├── chat.py
│   │   │   ├── resources.py
│   │   │   ├── notifications.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── assessment.py
│   │   │   ├── checkin.py
│   │   │   ├── medication.py
│   │   │   ├── safety.py
│   │   │   ├── chat.py
│   │   │   └── caregiver.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── assessment.py
│   │   │   ├── checkin.py
│   │   │   ├── medication.py
│   │   │   ├── safety_event.py
│   │   │   ├── conversation.py
│   │   │   ├── caregiver.py
│   │   │   └── audit_log.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── assessment_service.py
│   │   │   ├── checkin_service.py
│   │   │   ├── medication_service.py
│   │   │   ├── safety_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── notification_service.py
│   │   │   └── caregiver_service.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── user_repository.py
│   │   │   ├── assessment_repository.py
│   │   │   ├── checkin_repository.py
│   │   │   └── safety_repository.py
│   │   │
│   │   ├── security/
│   │   │   ├── authentication.py
│   │   │   ├── authorization.py
│   │   │   ├── permissions.py
│   │   │   └── encryption.py
│   │   │
│   │   ├── workers/
│   │   │   ├── notifications.py
│   │   │   ├── reminders.py
│   │   │   ├── trend_jobs.py
│   │   │   └── cleanup.py
│   │   │
│   │   └── core/
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── redis.py
│   │       └── logging.py
│   │
│   ├── migrations/
│   └── tests/
│
├── frontend/
│   ├── web/
│   └── mobile/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   ├── monitoring/
│   │   ├── prometheus/
│   │   └── grafana/
│   └── deployment/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── ml/
│   ├── rag/
│   ├── safety/
│   └── end_to_end/
│
├── notebooks/
│   ├── data_exploration/
│   ├── screening_analysis/
│   ├── model_experiments/
│   └── rag_evaluation/
│
├── docs/
│   ├── architecture/
│   │   ├── system_architecture.md
│   │   ├── database_design.md
│   │   └── api_architecture.md
│   │
│   ├── clinical/
│   │   ├── clinical_scope.md
│   │   ├── safety_protocol.md
│   │   └── screening_protocol.md
│   │
│   ├── ml_ai/
│   │   ├── model_card.md
│   │   ├── rag_design.md
│   │   └── evaluation.md
│   │
│   └── deployment/
│       ├── deployment.md
│       ├── monitoring.md
│       └── incident_response.md
│
└── scripts/
    ├── ingest_documents.py
    ├── build_embeddings.py
    ├── initialize_db.py
    └── run_evaluation.py