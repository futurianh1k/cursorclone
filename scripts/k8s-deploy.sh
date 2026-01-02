#!/bin/bash
set -e

# Kubernetes 배포 스크립트
# 사용법: ./scripts/k8s-deploy.sh [action]
# 예: ./scripts/k8s-deploy.sh deploy

ACTION=${1:-deploy}
NAMESPACE="cursor-poc"

echo "🚀 Kubernetes Deployment: ${ACTION}"

case $ACTION in
  deploy)
    echo "📦 Creating namespace..."
    kubectl apply -f k8s/namespace.yaml
    
    echo "📦 Creating secrets..."
    kubectl apply -f k8s/secrets.yaml || echo "⚠️  Secrets not found, please create them manually"
    
    echo "📦 Deploying PostgreSQL..."
    kubectl apply -f k8s/postgres.yaml
    
    echo "📦 Deploying Redis..."
    kubectl apply -f k8s/redis.yaml
    
    echo "⏳ Waiting for databases to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n ${NAMESPACE} --timeout=300s
    
    echo "📦 Deploying API..."
    kubectl apply -f k8s/api.yaml
    
    echo "📦 Deploying Web..."
    kubectl apply -f k8s/web.yaml
    
    echo "⏳ Waiting for deployments to be ready..."
    kubectl wait --for=condition=available deployment/api -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=available deployment/web -n ${NAMESPACE} --timeout=300s
    
    echo "✅ Deployment complete!"
    kubectl get all -n ${NAMESPACE}
    ;;
  
  update)
    echo "🔄 Updating deployments..."
    kubectl rollout restart deployment/api -n ${NAMESPACE}
    kubectl rollout restart deployment/web -n ${NAMESPACE}
    
    echo "⏳ Waiting for rollout to complete..."
    kubectl rollout status deployment/api -n ${NAMESPACE}
    kubectl rollout status deployment/web -n ${NAMESPACE}
    
    echo "✅ Update complete!"
    ;;
  
  delete)
    echo "🗑️  Deleting deployments..."
    kubectl delete -f k8s/ --ignore-not-found=true
    
    echo "✅ Deletion complete!"
    ;;
  
  status)
    echo "📊 Deployment Status:"
    kubectl get all -n ${NAMESPACE}
    echo ""
    echo "📈 Pod Status:"
    kubectl get pods -n ${NAMESPACE}
    echo ""
    echo "📉 HPA Status:"
    kubectl get hpa -n ${NAMESPACE}
    ;;
  
  logs)
    SERVICE=${2:-api}
    kubectl logs -f deployment/${SERVICE} -n ${NAMESPACE}
    ;;
  
  *)
    echo "❌ Unknown action: ${ACTION}"
    echo "Available actions: deploy, update, delete, status, logs"
    exit 1
    ;;
esac
