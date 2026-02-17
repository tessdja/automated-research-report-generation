## 🏗 Architecture Overview
### Application Load Balancer + ECS (Fargate) Architecture

This application is deployed using:
- Application Load Balancer (ALB) – internet-facing
- ECS Service (Fargate launch type)
- Target Group (IP target type)
- FastAPI application running on Uvicorn (port 8000)

### Traffic Flow
```
Client (Browser / curl)
        ↓
Internet
        ↓
Application Load Balancer (HTTP : 80)
        ↓
Target Group (HTTP : 8000)
        ↓
ECS Task (awsvpc mode)
        ↓
FastAPI app (/health endpoint)
```

### 🔄 End-to-End Request Flow (Technical Explanation)

1. A client sends a request to:
`http://arrg-alb-628324239.us-east-1.elb.amazonaws.com/health`

2. The ALB (port 80) receives the request.
3. The ALB forwards traffic to:
  - Target Group: arrg-tg
  -  Port: 8000
4. The Target Group routes to:
  - The ECS task’s private IP
  - Port 8000
5. The container is running:
`uvicorn research_and_analyst.api.main:app --host 0.0.0.0 --port 8000`
6. The FastAPI /health endpoint returns:
`{"status": "ok"}`
7. ALB marks the target as healthy.

## ❤️ Health Check Configuration (Design Rationale)
```
| Setting             | Value               |
| ------------------- | ------------------- |
| Protocol            | HTTP                |
| Port                | Traffic port (8000) |
| Path                | /health             |
| Interval            | 30 seconds          |
| Timeout             | 5 seconds           |
| Healthy threshold   | 5 successes         |
| Unhealthy threshold | 2 failures          |
| Success codes       | 200                 |
```
### Why `/health` is Used
Using a dedicated /health endpoint:
- Avoids checking complex routes
- Ensures the app is fully started
- Confirms routing, container networking, and application logic are functional
This ensures the load balancer only routes traffic to fully ready containers.

### Why 5 Healthy Checks?
With:
- Interval = 30s
- Healthy threshold = 5

The container must respond successfully for:
`5 × 30s = ~150 seconds`
before being marked healthy.

### Why this is good:
- Prevents premature routing during container warm-up
- Avoids sending traffic to half-initialized apps
- Reduces deploy instability

### Why Only 2 Unhealthy Checks?
If the app fails twice:
`2 × 30s = ~60 seconds`

The ALB removes it from service.
This provides:
- Fast failure detection
- Automatic traffic rerouting
- Built-in high availability behavior

## 🚨 Incident Summary (Why 503 Occurred)
### Symptom
ALB returned:
`HTTP/1.1 503 Service Temporarily Unavailable`
`Server: awselb/2.0`

### Root Cause
The target group had:
`0 registered targets`

Therefore:
- ALB was reachable
- Listener was configured
- But there were no healthy backend tasks to route to

ALB correctly returned **503.**

### Resolution
- ECS service was properly associated with:
        - Target group arrg-tg
        - Container port 8000
- ECS automatically registered the task IP
 Health checks to /health passed
- Target marked healthy
- 503 resolved

### 🎯 503 Explanation (One Paragraph)
The initial 503 error occurred because the Application Load Balancer had no healthy ECS task targets registered in its target group. Although the ALB was internet-facing and correctly configured, traffic could not be routed to any backend container. Once the ECS service was properly attached to the target group and passed health checks on /health, the ALB began routing traffic successfully, restoring service availability.

### 🧠 What You Just Built (Big Picture)
You now have:
- Dynamic container deployment
- Automatic service registration/deregistration
- Health-based traffic routing
- Fault isolation
- Production-style architecture

This is not a “basic deployment” anymore — this is real cloud-native infrastructure.

## 🚀 CI/CD Deployment Architecture (GitHub Actions → ECS)
In addition to the runtime architecture, this system includes an automated deployment pipeline using GitHub Actions.

### Deployment Trigger
- A push to the main branch automatically triggers a GitHub Actions workflow.
- The workflow builds, publishes, and deploys a new container revision to ECS.
### 🔄 CI/CD Flow
```
Developer Push to main
        ↓
GitHub Actions Workflow
        ↓
Build Docker Image
        ↓
Push Image to Amazon ECR
        ↓
Render ECS Task Definition (new image tag)
        ↓
Register New Task Definition Revision
        ↓
Update ECS Service
        ↓
Rolling Deployment
        ↓
ALB Health Check (/health)
        ↓
Traffic Routed to New Container
```
### 🔍 Technical Breakdown
1. Developer pushes code to main.
2. GitHub Actions:
  - Configures AWS credentials
  - Logs into Amazon ECR
  - Builds Docker image
  - Pushes image to ECR
3. Workflow renders a new task definition with updated image.
4. ECS registers a new task definition revision.
5. ECS service performs a rolling update:
  - Starts new task
  - Waits for /health to pass
  - Stops old task
6. ALB routes traffic only to healthy tasks.

### 🎯 Why This Matters
This pipeline provides:
- Automated deployments
- Consistent container builds
- Immutable infrastructure revisions
- Zero manual ECS updates
- Repeatable production deployments
- Rollback capability via task definition revisions

### 🏗 Updated Big Picture Architecture
You now have two layers:

### Runtime Layer (Traffic Handling)
Client → ALB → Target Group → ECS (Fargate) → FastAPI

### Delivery Layer (CI/CD)
GitHub → GitHub Actions → ECR → ECS → ALB

This separation ensures:
- Clean deployment lifecycle
- Infrastructure automation
- Production-grade cloud architecture

### 🎯 Summary
The application now includes a fully automated CI/CD pipeline. Code changes pushed to the main branch automatically build a new container image, publish it to Amazon ECR, register a new ECS task revision, and deploy it using rolling updates. Health checks ensure only healthy containers receive traffic, enabling safe, production-ready deployments without manual intervention.