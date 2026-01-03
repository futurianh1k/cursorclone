#!/bin/bash
# ===========================================
# VDE Web IDE Platform - User Provisioning Script
# 용도: 새 사용자를 위한 워크스페이스 프로비저닝
# ===========================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 사용법
usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
    create <user_id>     Create workspace for a new user
    delete <user_id>     Delete user workspace (preserves data)
    list                 List all user workspaces
    status <user_id>     Check user workspace status

Options:
    -h, --help          Show this help message
    -f, --force         Force operation (skip confirmation)
    -n, --namespace     Kubernetes namespace (default: vde-ide)

Examples:
    $0 create user123
    $0 delete user123 --force
    $0 list
EOF
}

# 설정
NAMESPACE="${NAMESPACE:-vde-ide}"
STORAGE_CLASS="${STORAGE_CLASS:-fast-ssd}"
WORKSPACE_SIZE="${WORKSPACE_SIZE:-20Gi}"
CPU_REQUEST="${CPU_REQUEST:-500m}"
CPU_LIMIT="${CPU_LIMIT:-2}"
MEMORY_REQUEST="${MEMORY_REQUEST:-1Gi}"
MEMORY_LIMIT="${MEMORY_LIMIT:-4Gi}"

# 사용자 워크스페이스 생성
create_workspace() {
    local user_id=$1
    local user_namespace="ide-${user_id}"
    
    log_info "Creating workspace for user: ${user_id}"
    
    # 네임스페이스 존재 확인
    if kubectl get namespace "${user_namespace}" &> /dev/null; then
        log_warn "Namespace ${user_namespace} already exists"
        return 1
    fi
    
    # 네임스페이스 생성
    log_info "Creating namespace: ${user_namespace}"
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: ${user_namespace}
  labels:
    user: "${user_id}"
    app.kubernetes.io/part-of: vde-web-ide
    type: user-workspace
EOF

    # ResourceQuota 생성
    log_info "Creating ResourceQuota"
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: user-quota
  namespace: ${user_namespace}
spec:
  hard:
    requests.cpu: "${CPU_LIMIT}"
    requests.memory: "${MEMORY_LIMIT}"
    limits.cpu: "$((${CPU_LIMIT%?} * 2))${CPU_LIMIT: -1}"
    limits.memory: "8Gi"
    persistentvolumeclaims: "2"
    requests.storage: "${WORKSPACE_SIZE}"
EOF

    # NetworkPolicy 생성
    log_info "Creating NetworkPolicy"
    cat << EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: user-network-policy
  namespace: ${user_namespace}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ${NAMESPACE}
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              shared: "true"
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
EOF

    # PVC 생성
    log_info "Creating PersistentVolumeClaim"
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: workspace-${user_id}
  namespace: ${user_namespace}
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ${STORAGE_CLASS}
  resources:
    requests:
      storage: ${WORKSPACE_SIZE}
EOF

    # code-server Pod 생성
    log_info "Creating code-server Pod"
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: code-server-${user_id}
  namespace: ${user_namespace}
  labels:
    app: code-server
    user: "${user_id}"
spec:
  containers:
    - name: code-server
      image: codercom/code-server:4.96.4
      ports:
        - containerPort: 8080
      env:
        - name: USER_ID
          value: "${user_id}"
      resources:
        requests:
          cpu: "${CPU_REQUEST}"
          memory: "${MEMORY_REQUEST}"
        limits:
          cpu: "${CPU_LIMIT}"
          memory: "${MEMORY_LIMIT}"
      volumeMounts:
        - name: workspace
          mountPath: /home/coder
  volumes:
    - name: workspace
      persistentVolumeClaim:
        claimName: workspace-${user_id}
EOF

    # Service 생성
    log_info "Creating Service"
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: code-server-${user_id}
  namespace: ${user_namespace}
spec:
  selector:
    user: "${user_id}"
  ports:
    - port: 8080
      targetPort: 8080
EOF

    log_info "Workspace created successfully for user: ${user_id}"
    log_info "Namespace: ${user_namespace}"
    
    # 감사 로그
    echo "$(date -Iseconds) | ${ADMIN_USER:-system} | CREATE | ${user_id}" >> /var/log/vde-ide/user-audit.log 2>/dev/null || true
}

# 사용자 워크스페이스 삭제
delete_workspace() {
    local user_id=$1
    local force=${2:-false}
    local user_namespace="ide-${user_id}"
    
    if ! kubectl get namespace "${user_namespace}" &> /dev/null; then
        log_error "Namespace ${user_namespace} does not exist"
        return 1
    fi
    
    if [ "$force" != "true" ]; then
        read -p "Are you sure you want to delete workspace for ${user_id}? (y/N) " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log_info "Cancelled"
            return 0
        fi
    fi
    
    log_info "Deleting workspace for user: ${user_id}"
    
    # Pod 삭제 (데이터는 보존)
    kubectl delete pod -n "${user_namespace}" --all --grace-period=30
    
    # 네임스페이스에 비활성화 주석 추가 (감사 목적으로 보존)
    kubectl annotate namespace "${user_namespace}" \
        "disabled-at=$(date -Iseconds)" \
        "disabled-by=${ADMIN_USER:-system}" \
        --overwrite
    
    log_warn "Workspace disabled. PVC preserved for audit. To fully delete:"
    log_warn "  kubectl delete namespace ${user_namespace}"
    
    # 감사 로그
    echo "$(date -Iseconds) | ${ADMIN_USER:-system} | DELETE | ${user_id}" >> /var/log/vde-ide/user-audit.log 2>/dev/null || true
}

# 워크스페이스 목록
list_workspaces() {
    log_info "User Workspaces:"
    kubectl get namespaces -l type=user-workspace -o custom-columns=\
"NAMESPACE:.metadata.name,USER:.metadata.labels.user,CREATED:.metadata.creationTimestamp,STATUS:.status.phase"
}

# 워크스페이스 상태 확인
check_status() {
    local user_id=$1
    local user_namespace="ide-${user_id}"
    
    if ! kubectl get namespace "${user_namespace}" &> /dev/null; then
        log_error "Namespace ${user_namespace} does not exist"
        return 1
    fi
    
    log_info "Workspace status for user: ${user_id}"
    echo ""
    
    echo "=== Pod Status ==="
    kubectl get pods -n "${user_namespace}" -o wide
    echo ""
    
    echo "=== PVC Status ==="
    kubectl get pvc -n "${user_namespace}"
    echo ""
    
    echo "=== Resource Usage ==="
    kubectl top pods -n "${user_namespace}" 2>/dev/null || echo "Metrics not available"
}

# 메인 함수
main() {
    if [ $# -lt 1 ]; then
        usage
        exit 1
    fi
    
    local command=$1
    shift
    
    case $command in
        create)
            if [ $# -lt 1 ]; then
                log_error "User ID required"
                usage
                exit 1
            fi
            create_workspace "$1"
            ;;
        delete)
            if [ $# -lt 1 ]; then
                log_error "User ID required"
                usage
                exit 1
            fi
            local force=false
            if [ "${2:-}" = "-f" ] || [ "${2:-}" = "--force" ]; then
                force=true
            fi
            delete_workspace "$1" "$force"
            ;;
        list)
            list_workspaces
            ;;
        status)
            if [ $# -lt 1 ]; then
                log_error "User ID required"
                usage
                exit 1
            fi
            check_status "$1"
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
