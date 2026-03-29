#!/usr/bin/env bash
# Interactive demo walkthrough for the CRD/CR/Controller demo.
set -euo pipefail

CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

step() { echo -e "\n${CYAN}${BOLD}==> $*${RESET}"; }
info() { echo -e "${YELLOW}    $*${RESET}"; }
ok()   { echo -e "${GREEN}    $*${RESET}"; }

pause() {
  echo -e "\n${BOLD}[Press ENTER to continue...]${RESET}"
  read -r
}

# ── 1. Show the cluster is healthy ──────────────────────────────────────────
step "Step 1 — Cluster is healthy"
kubectl cluster-info --context kind-demo-cluster
pause

# ── 2. External API health check ────────────────────────────────────────────
step "Step 2 — External API health check"
info "The FastAPI message board runs OUTSIDE the kind cluster as a plain Docker container."
curl -s http://localhost:8080/ | python3 -m json.tool
pause

# ── 3. Show the CRD ─────────────────────────────────────────────────────────
step "Step 3 — Inspect the CRD"
kubectl get crd messages.demo.example.com
echo ""
kubectl explain message.spec
pause

# ── 4. Boards are empty ─────────────────────────────────────────────────────
step "Step 4 — No messages yet"
info "External API boards list:"
curl -s http://localhost:8080/boards | python3 -m json.tool
pause

# ── 5. Create the hello-world message ───────────────────────────────────────
step "Step 5 — Create a Message CR"
info "Applying manifests/samples/message-hello.yaml..."
kubectl apply -f manifests/samples/message-hello.yaml
echo ""
info "Waiting for controller to post it to the external API..."
for i in $(seq 1 30); do
  PHASE=$(kubectl get message hello-world -n demo -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [[ "$PHASE" == "Posted" ]]; then
    ok "Phase = Posted"
    break
  fi
  sleep 1
done
echo ""
kubectl get messages -n demo
pause

# ── 6. Check the external API ───────────────────────────────────────────────
step "Step 6 — Message is now in the external API"
curl -s http://localhost:8080/boards/general | python3 -m json.tool
pause

# ── 7. Create a second message on a different board ─────────────────────────
step "Step 7 — Create a second Message on the 'farewells' board"
kubectl apply -f manifests/samples/message-goodbye.yaml
for i in $(seq 1 30); do
  PHASE=$(kubectl get message goodbye-world -n demo -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [[ "$PHASE" == "Posted" ]]; then
    ok "Phase = Posted"
    break
  fi
  sleep 1
done
echo ""
kubectl get messages -n demo
echo ""
info "External API boards:"
curl -s http://localhost:8080/boards | python3 -m json.tool
pause

# ── 8. Update the hello-world message ───────────────────────────────────────
step "Step 8 — Update the hello-world Message CR"
info "Applying manifests/samples/message-update.yaml (title changed)..."
kubectl apply -f manifests/samples/message-update.yaml
for i in $(seq 1 30); do
  PHASE=$(kubectl get message hello-world -n demo -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [[ "$PHASE" == "Updated" ]]; then
    ok "Phase = Updated"
    break
  fi
  sleep 1
done
echo ""
info "External API now shows the updated title:"
curl -s http://localhost:8080/boards/general | python3 -m json.tool
pause

# ── 9. Delete the goodbye-world message ─────────────────────────────────────
step "Step 9 — Delete a Message CR (controller removes it from external API)"
kubectl delete message goodbye-world -n demo
info "Waiting for deletion to propagate..."
sleep 3
echo ""
info "External API farewells board (should be empty):"
curl -s http://localhost:8080/boards/farewells | python3 -m json.tool
pause

# ── 10. Show controller logs ─────────────────────────────────────────────────
step "Step 10 — Recent controller logs"
kubectl logs -n demo -l app=message-controller --tail=40
pause

# ── Final summary ────────────────────────────────────────────────────────────
step "Demo complete!"
echo ""
ok "What we demonstrated:"
echo "  1. A CRD (CustomResourceDefinition) extends the Kubernetes API with a 'Message' type."
echo "  2. A kopf controller watches Message CRs inside the kind cluster."
echo "  3. On create/update/delete, the controller calls an external FastAPI service."
echo "  4. Kubernetes acted as a control plane for a non-Kubernetes resource."
echo ""
info "To clean up: make teardown"
