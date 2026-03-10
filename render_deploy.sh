#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  render_deploy.sh  —  HDInsight Heart Disease Analysis
#  One-shot deployment prep for Render.com (free tier compatible)
#
#  Usage:  bash render_deploy.sh
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERR]${NC}   $*"; }
step()    { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}"; }
hr()      { echo -e "${CYAN}─────────────────────────────────────────────${NC}"; }

# ── Banner ────────────────────────────────────────────────────────
clear
echo -e "${RED}${BOLD}"
cat << 'BANNER'
 ██╗  ██╗██████╗ ██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗
 ██║  ██║██╔══██╗██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
 ███████║██║  ██║██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║   
 ██╔══██║██║  ██║██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║   
 ██║  ██║██████╔╝██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║   
 ╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝  
         Heart Disease Analytics — Render.com Deployment
BANNER
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Working directory: $SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Pre-flight checks
# ═══════════════════════════════════════════════════════════════════
step "Step 1: Pre-flight checks"

REQUIRED_FILES=(
  "app.py" "db_setup.py" "analysis.py"
  "requirements.txt" "render.yaml" "gunicorn.conf.py"
  "Heart_new2.csv" "templates/base.html"
  "static/css/style.css" "static/js/main.js"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    success "Found: $f"
  else
    error "Missing: $f"
    ALL_OK=false
  fi
done

if [[ "$ALL_OK" == false ]]; then
  error "Required files missing. Run the project builder first."
  exit 1
fi

# Check gunicorn is in requirements.txt
if grep -q "gunicorn" requirements.txt; then
  success "gunicorn is in requirements.txt"
else
  warn "Adding gunicorn to requirements.txt"
  echo "gunicorn==21.2.0" >> requirements.txt
fi

# Check git is installed
if ! command -v git &>/dev/null; then
  error "git is not installed. Install it with: sudo apt install git"
  exit 1
fi
success "git is available"

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Quick local smoke test
# ═══════════════════════════════════════════════════════════════════
step "Step 2: Local smoke test"

PYTHON_BIN=""
for py in ".venv/bin/python" "python3" "python"; do
  if command -v "$py" &>/dev/null || [[ -f "$py" ]]; then
    PYTHON_BIN="$py"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  error "No Python interpreter found."
  exit 1
fi
success "Python: $($PYTHON_BIN --version 2>&1)"

info "Testing DB initialisation..."
$PYTHON_BIN db_setup.py
success "Database initialised successfully"

info "Testing chart generation (quick import check)..."
$PYTHON_BIN -c "
import analysis
k = analysis.get_kpis()
print(f'  KPIs OK → total={k[\"total\"]}, hd_pct={k[\"hd_pct\"]}%')
c = analysis.chart_hd_distribution()
print(f'  Charts OK → sample length={len(c)}')
"
success "Analysis module verified"

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — Git repository setup
# ═══════════════════════════════════════════════════════════════════
step "Step 3: Git repository setup"

if [[ ! -d ".git" ]]; then
  info "Initialising git repository..."
  git init -b main
  success "Git repository initialised"
else
  success "Git repository already exists"
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  info "Current branch: $CURRENT_BRANCH"
fi

# Configure git user if not set
GIT_NAME=$(git config --global user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")

if [[ -z "$GIT_NAME" ]]; then
  read -rp "$(echo -e "${YELLOW}Enter your git user name:${NC} ")" GIT_NAME
  git config --global user.name "$GIT_NAME"
fi
if [[ -z "$GIT_EMAIL" ]]; then
  read -rp "$(echo -e "${YELLOW}Enter your git email:${NC} ")" GIT_EMAIL
  git config --global user.email "$GIT_EMAIL"
fi
success "Git user: $GIT_NAME <$GIT_EMAIL>"

# ── .gitignore ────────────────────────────────────────────────────
if [[ -f ".gitignore" ]]; then
  success ".gitignore present"
else
  warn "Creating minimal .gitignore"
  cat > .gitignore << 'GITIGNORE'
.venv/
__pycache__/
*.pyc
data/*.db
nohup.out
*.log
.DS_Store
GITIGNORE
fi

# ── Stage all files ───────────────────────────────────────────────
info "Staging files for commit..."
git add .
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
success "Staged $STAGED file(s)"

# ── Commit ────────────────────────────────────────────────────────
if git diff --cached --quiet; then
  warn "Nothing new to commit (already up to date)"
else
  COMMIT_MSG="Deploy: HDInsight Heart Disease Analytics Platform

- 4,500 patient records loaded into SQLite (5 SQL views)
- 13 interactive Plotly visualisations
- 4 dynamic dashboard filters
- 3-scene data story (Dr Sharma, Ramesh, Anita)
- Performance testing page
- Flask 3.0 + Gunicorn production server
- Render.com deployment ready"

  git commit -m "$COMMIT_MSG"
  success "Committed: $(git log --oneline -1)"
fi

# ═══════════════════════════════════════════════════════════════════
# STEP 4 — GitHub remote setup
# ═══════════════════════════════════════════════════════════════════
step "Step 4: GitHub remote configuration"

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

if [[ -n "$REMOTE_URL" ]]; then
  success "Remote already set: $REMOTE_URL"
else
  hr
  echo -e "${YELLOW}No GitHub remote found. You need a GitHub repository.${NC}"
  echo ""
  echo -e "  1. Go to ${CYAN}https://github.com/new${NC}"
  echo "  2. Create a NEW EMPTY repository (no README, no .gitignore)"
  echo "  3. Copy the SSH or HTTPS URL"
  echo ""
  read -rp "$(echo -e "${YELLOW}Paste your GitHub repository URL (e.g. https://github.com/you/repo.git):${NC} ")" REMOTE_URL
  if [[ -z "$REMOTE_URL" ]]; then
    error "No URL provided. Exiting."
    exit 1
  fi
  git remote add origin "$REMOTE_URL"
  success "Remote added: $REMOTE_URL"
fi

# ═══════════════════════════════════════════════════════════════════
# STEP 5 — Push to GitHub
# ═══════════════════════════════════════════════════════════════════
step "Step 5: Push to GitHub"

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
info "Pushing branch '$BRANCH' to origin..."

if git push -u origin "$BRANCH" --force-with-lease 2>&1; then
  success "Pushed to GitHub successfully!"
else
  warn "Push failed with --force-with-lease, retrying with --force..."
  git push -u origin "$BRANCH" --force
  success "Pushed to GitHub (force)"
fi

# ═══════════════════════════════════════════════════════════════════
# STEP 6 — Render deployment instructions
# ═══════════════════════════════════════════════════════════════════
step "Step 6: Deploy on Render.com"

REPO_URL=$(git remote get-url origin | sed 's/\.git$//')
hr
echo ""
echo -e "${BOLD}${GREEN}✅ Code is on GitHub. Now deploy on Render:${NC}"
echo ""
echo -e "${BOLD}Option A — Blueprint (Automatic, uses render.yaml):${NC}"
echo ""
echo -e "  1. Go to ${CYAN}https://dashboard.render.com/select-repo${NC}"
echo -e "  2. Select: ${CYAN}$REPO_URL${NC}"
echo -e "  3. Render auto-detects ${BOLD}render.yaml${NC} → click ${BOLD}Apply${NC}"
echo -e "  4. Wait ~3-5 minutes for build to complete"
echo ""
echo -e "${BOLD}Option B — Manual Web Service:${NC}"
echo ""
echo -e "  1. ${CYAN}https://dashboard.render.com/web/new${NC}"
echo -e "  2. Connect your GitHub repo: ${CYAN}$REPO_URL${NC}"
echo -e "  3. Fill in:"
echo -e "     • ${BOLD}Name:${NC}            hdinsight-heart-disease"
echo -e "     • ${BOLD}Runtime:${NC}         Python 3"
echo -e "     • ${BOLD}Build Command:${NC}   pip install -r requirements.txt"
echo -e "     • ${BOLD}Start Command:${NC}   python db_setup.py && gunicorn app:app -c gunicorn.conf.py"
echo -e "     • ${BOLD}Plan:${NC}            Free"
echo -e "  4. Click ${BOLD}Create Web Service${NC}"
echo ""
echo -e "${BOLD}Environment Variables to set on Render:${NC}"
echo -e "  ${YELLOW}FLASK_ENV${NC}         = production"
echo -e "  ${YELLOW}PYTHON_VERSION${NC}    = 3.12.3"
echo -e "  ${YELLOW}WEB_CONCURRENCY${NC}   = 2"
echo ""
hr
echo ""
echo -e "${BOLD}After deployment your app will be live at:${NC}"
echo -e "  ${CYAN}https://hdinsight-heart-disease.onrender.com${NC}"
echo ""
echo -e "${YELLOW}Note (Free tier):${NC} The instance sleeps after 15 min of inactivity."
echo -e "First request after sleep takes ~30s to wake up."
echo -e "Upgrade to ${BOLD}Starter ($7/mo)${NC} for always-on service."
echo ""
hr
echo ""
echo -e "${GREEN}${BOLD}🚀 Deployment prep complete!${NC}"
echo ""
