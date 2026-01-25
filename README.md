# sleeping-beauty

Personal sleep monitoring and analysis.

This project ingests a subset of my wearable sleep data,
normalizes it, and feeds it into a fixed LLM prompt to
produce interpretable, longitudinal sleep insights.

This is a personal system, not a general sleep platform.

## Webhooks

Webhooks not working right now. Oura is looking into it now.

## Running webhook listener

```bash
uvicorn sleeping_beauty.ingress.main:app --host 0.0.0.0 --port nnnn --reload
```

## Running webhook registration

### Get list of current registrations
```bash
uv run scripts/register_oura_webhook.py --list-only
```

``` text
Existing webhook subscriptions (will be deleted):
- id=e1bed68a-4a3a-48bd-aa4d-3de978eec7f8 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_activity/create
- id=edfd4661-1fd3-4d93-9ffa-d451ce5d47df url=https://oura.hicsvntdracons.xyz/oura/webhook daily_activity/delete
- id=afd067be-fc03-429b-a762-08e133f8b54c url=https://oura.hicsvntdracons.xyz/oura/webhook daily_activity/update
- id=3db6bfc0-eb26-47a7-8568-1cc9e22787bd url=https://oura.hicsvntdracons.xyz/oura/webhook daily_cardiovascular_age/create
- id=ffe80dba-b262-4c02-b59d-25b4efd377db url=https://oura.hicsvntdracons.xyz/oura/webhook daily_cardiovascular_age/delete
- id=00b7bff7-7a18-4b9d-8db8-5f0ad9ea081c url=https://oura.hicsvntdracons.xyz/oura/webhook daily_cardiovascular_age/update
- id=c8547221-f7c7-48d5-a65f-c36a7767b71d url=https://oura.hicsvntdracons.xyz/oura/webhook daily_readiness/create
- id=67ed0fa0-fe73-4249-bb97-455b4f6b3da2 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_readiness/delete
- id=858f87f9-9917-4b66-81c7-70909f2b1d35 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_readiness/update
- id=fc9618ab-98a1-4d66-9bee-7cb576e8307f url=https://oura.hicsvntdracons.xyz/oura/webhook daily_resilience/create
- id=59337b93-9870-4fb9-bdfe-802736d4dc17 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_resilience/delete
- id=0cd1d0f0-cec8-41ad-b8f6-fed8cc22d702 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_resilience/update
- id=32a7525d-db7a-4bef-95e7-6380c1402ed5 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_sleep/create
- id=30d40433-7b9a-4bfd-9214-a3c9ae52b655 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_sleep/delete
- id=a5d6a883-050d-40c3-a212-50ffea8a2a36 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_sleep/update
- id=884b3162-e4f1-4473-a14e-0b28cd933e20 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_spo2/create
- id=356a9027-1c2d-41eb-a205-aac31f8596b9 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_spo2/delete
- id=6943282e-c956-4a4e-b222-2694a4a1faf7 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_spo2/update
- id=a5c0317c-0145-4ab5-8797-5c826ac997e6 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_stress/create
- id=073399c6-e100-468b-9014-d34bae785d49 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_stress/delete
- id=cdaa696c-09dd-42d5-b49a-4856e353e9b1 url=https://oura.hicsvntdracons.xyz/oura/webhook daily_stress/update
- id=564775a0-22eb-4855-9497-2defa73b48d9 url=https://oura.hicsvntdracons.xyz/oura/webhook enhanced_tag/create
- id=d0b0ec7f-9349-47be-8421-bf0182c2765d url=https://oura.hicsvntdracons.xyz/oura/webhook enhanced_tag/delete
- id=fc169634-20d1-476b-b54e-d9be37f5b510 url=https://oura.hicsvntdracons.xyz/oura/webhook enhanced_tag/update
- id=a8ab8e7d-89a3-48bd-bc55-787a3d56cd27 url=https://oura.hicsvntdracons.xyz/oura/webhook rest_mode_period/create
- id=996283b9-ead5-4bf2-85e4-05fe2b8cea85 url=https://oura.hicsvntdracons.xyz/oura/webhook rest_mode_period/delete
- id=5f8d018a-a7db-4d63-85da-a7b51345895c url=https://oura.hicsvntdracons.xyz/oura/webhook rest_mode_period/update
- id=2ec0d733-2b3c-49a2-aa56-9d006695c718 url=https://oura.hicsvntdracons.xyz/oura/webhook ring_configuration/create
- id=1f3ed50c-4f5d-460b-bfc3-53286812e158 url=https://oura.hicsvntdracons.xyz/oura/webhook ring_configuration/delete
- id=484947b7-b882-4578-a270-c44f8b1ecc3d url=https://oura.hicsvntdracons.xyz/oura/webhook ring_configuration/update
- id=fcc88dd4-f1b1-4c6b-b9f1-90f39d77d5b7 url=https://oura.hicsvntdracons.xyz/oura/webhook session/create
- id=bd8b4c83-245c-46e2-8402-40d449e4def3 url=https://oura.hicsvntdracons.xyz/oura/webhook session/delete
- id=da6b9639-707f-4dc8-bc72-77923fd87fcd url=https://oura.hicsvntdracons.xyz/oura/webhook session/update
- id=523b0643-07b3-4d07-936c-9b46cdb6bdbf url=https://oura.hicsvntdracons.xyz/oura/webhook sleep/create
- id=75095b72-e26b-4835-a124-82111fa5515f url=https://oura.hicsvntdracons.xyz/oura/webhook sleep/delete
- id=212bfba0-4f9c-40c8-9bf9-63842de0a8b4 url=https://oura.hicsvntdracons.xyz/oura/webhook sleep/update
- id=22b474df-3629-45de-8701-ec795457e3a0 url=https://oura.hicsvntdracons.xyz/oura/webhook sleep_time/create
- id=fbd513bf-19ea-45a8-8ebc-bcb46ddb742d url=https://oura.hicsvntdracons.xyz/oura/webhook sleep_time/delete
- id=72484f09-e7a8-4605-a159-bfbe3ee97ccb url=https://oura.hicsvntdracons.xyz/oura/webhook sleep_time/update
- id=5d469b73-0285-420f-a9be-5166ece276c1 url=https://oura.hicsvntdracons.xyz/oura/webhook tag/create
- id=81398277-92ea-4f79-8bfe-9702cfc62542 url=https://oura.hicsvntdracons.xyz/oura/webhook tag/delete
- id=48e87550-f559-4f10-8bdb-6c7c18b0d3d8 url=https://oura.hicsvntdracons.xyz/oura/webhook tag/update
- id=495d1064-6b35-4fef-9b4d-234ad047c5f8 url=https://oura.hicsvntdracons.xyz/oura/webhook vo2_max/create
- id=e0408405-762a-4210-b025-54d8869f2196 url=https://oura.hicsvntdracons.xyz/oura/webhook vo2_max/delete
- id=7cdc2354-11a4-4f38-b6ab-0fe3cc9f8fab url=https://oura.hicsvntdracons.xyz/oura/webhook vo2_max/update
- id=434faf5e-726d-4c25-9ac3-b758ca07fd74 url=https://oura.hicsvntdracons.xyz/oura/webhook workout/create
- id=747b0b9e-a615-4635-a4f9-487b5130d393 url=https://oura.hicsvntdracons.xyz/oura/webhook workout/delete
- id=56213c41-062c-4968-ac28-c2025d2364ae url=https://oura.hicsvntdracons.xyz/oura/webhook workout/update
```

### Delete current hooks and register new

```bash
uv run scripts/register_oura_webhook.py
```