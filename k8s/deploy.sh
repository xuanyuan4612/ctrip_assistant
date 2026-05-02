#!/usr/bin/env bash
# =============================================================================
# deploy.sh - Deployment script for Ctrip Assistant
#
# Usage:
#   ./deploy.sh staging          Deploy to staging
#   ./deploy.sh production       Deploy to production
#   ./deploy.sh staging:migrate  Deploy + run DB migrations
#   ./deploy.sh production:migrate  Deploy + run DB migrations
#
# Requirements:
#   - kubectl configured with the target cluster context
#   - kustomize (built into kubectl v1.14+)
# =============================================================================

set -euo pipefail

# ─── Color output ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── Argument parsing ────────────────────────────────────────────────────────
ENV="${1:-}"
if [[ -z "$ENV" ]]; then
    error "Usage: $0 {staging|production}[:migrate]"
    exit 1
fi

RUN_MIGRATIONS=false
if [[ "$ENV" == *:migrate ]]; then
    RUN_MIGRATIONS=true
    ENV="${ENV%%:migrate}"
fi

if [[ "$ENV" != "staging" && "$ENV" != "production" ]]; then
    error "Environment must be 'staging' or 'production', got '$ENV'"
    exit 1
fi

OVERLAY_DIR="$(cd "$(dirname "$0")/overlays/$ENV" && pwd)"
NAMESPACE="ctrip-assistant"

# ─── Pre-flight checks ───────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    error "kubectl is not installed."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
fi

info "Deploying to: ${ENV}"
info "Overlay:      ${OVERLAY_DIR}"
echo ""

# ─── Deploy ──────────────────────────────────────────────────────────────────
info "Applying Kubernetes manifests (kustomize)..."
if ! kubectl apply -k "$OVERLAY_DIR" --wait=true; then
    error "kubectl apply failed."
    exit 1
fi
success "Manifests applied successfully."

# ─── Wait for rollouts ───────────────────────────────────────────────────────
info "Waiting for backend rollout to complete..."
if kubectl rollout status deployment/ctrip-app-backend -n "$NAMESPACE" --timeout=300s; then
    success "Backend rollout complete."
else
    warn "Backend rollout timed out. Check pod status with: kubectl get pods -n $NAMESPACE"
fi

info "Waiting for frontend rollout to complete..."
if kubectl rollout status deployment/ctrip-frontend -n "$NAMESPACE" --timeout=300s; then
    success "Frontend rollout complete."
else
    warn "Frontend rollout timed out. Check pod status with: kubectl get pods -n $NAMESPACE"
fi

info "Waiting for Redis rollout to complete..."
if kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=120s; then
    success "Redis rollout complete."
else
    warn "Redis rollout timed out."
fi

info "Waiting for MySQL StatefulSet rollout to complete..."
if kubectl rollout status statefulset/mysql -n "$NAMESPACE" --timeout=300s; then
    success "MySQL rollout complete."
else
    warn "MySQL rollout timed out."
fi

echo ""

# ─── Database Migrations ─────────────────────────────────────────────────────
if [[ "$RUN_MIGRATIONS" == true ]]; then
    info "Running database migrations (alembic upgrade head)..."
    # Get the first ready backend pod
    BACKEND_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [[ -z "$BACKEND_POD" ]]; then
        warn "No backend pod found. Skipping migrations."
    else
        info "Executing alembic upgrade head on pod: $BACKEND_POD"
        if kubectl exec "$BACKEND_POD" -n "$NAMESPACE" -- alembic upgrade head; then
            success "Database migrations applied successfully."
        else
            error "Database migrations failed. Check the pod logs:"
            error "  kubectl logs $BACKEND_POD -n $NAMESPACE"
            exit 1
        fi
    fi
else
    info "Skipping database migrations. Run with ':migrate' suffix to run them."
    info "  $0 ${ENV}:migrate"
fi

echo ""

# ─── Summary ─────────────────────────────────────────────────────────────────
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
success "Deployment to ${ENV} completed successfully!"
echo ""
info "Resources:"
kubectl get all -n "$NAMESPACE" -l app.kubernetes.io/name=ctrip-assistant
echo ""
info "Ingress endpoints:"
kubectl get ingress -n "$NAMESPACE"
echo ""
if [[ "$ENV" == "production" ]]; then
    info "Production URL: https://assistant.ctrip.com"
else
    info "Staging URL:    https://staging.ctrip.example.com"
fi
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
