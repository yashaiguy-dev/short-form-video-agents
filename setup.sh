#!/bin/bash
# YT-to-Shorts — One-Command Setup (Mac / Linux)
# Run: bash setup.sh
# Installs everything needed to run the pipeline.

set -e

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
fail() { echo -e "  ${RED}[MISSING]${NC} $1"; }
info() { echo -e "  ${YELLOW}[INSTALLING]${NC} $1"; }

echo ""
echo "============================================"
echo "  YT-to-Shorts — Automatic Setup"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

ERRORS=0

# ─────────────────────────────────────────────
# 1. Detect OS
# ─────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "linux"* ]]; then
    OS="linux"
fi
echo "Detected OS: $OS"
echo ""

# ─────────────────────────────────────────────
# 2. Homebrew (Mac only)
# ─────────────────────────────────────────────
if [[ "$OS" == "mac" ]]; then
    echo "Checking Homebrew..."
    if command -v brew &>/dev/null; then
        ok "Homebrew already installed"
    else
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for Apple Silicon Macs
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        ok "Homebrew installed"
    fi
    echo ""
fi

# ─────────────────────────────────────────────
# 3. Python 3
# ─────────────────────────────────────────────
echo "Checking Python 3..."
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PY_VERSION"
else
    info "Installing Python 3..."
    if [[ "$OS" == "mac" ]]; then
        brew install python
    elif [[ "$OS" == "linux" ]]; then
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
    fi
    if command -v python3 &>/dev/null; then
        ok "Python 3 installed"
    else
        fail "Python 3 — install manually from python.org"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# ─────────────────────────────────────────────
# 4. pip3
# ─────────────────────────────────────────────
echo "Checking pip3..."
if command -v pip3 &>/dev/null; then
    ok "pip3 available"
else
    info "Installing pip3..."
    if [[ "$OS" == "mac" ]]; then
        python3 -m ensurepip --upgrade 2>/dev/null || brew install python
    elif [[ "$OS" == "linux" ]]; then
        sudo apt install -y python3-pip
    fi
    if command -v pip3 &>/dev/null; then
        ok "pip3 installed"
    else
        fail "pip3 — try: python3 -m ensurepip --upgrade"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# ─────────────────────────────────────────────
# 5. FFmpeg
# ─────────────────────────────────────────────
echo "Checking FFmpeg..."
if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg available"
else
    info "Installing FFmpeg..."
    if [[ "$OS" == "mac" ]]; then
        brew install ffmpeg
    elif [[ "$OS" == "linux" ]]; then
        sudo apt install -y ffmpeg
    fi
    if command -v ffmpeg &>/dev/null; then
        ok "ffmpeg installed"
    else
        fail "ffmpeg — install manually: brew install ffmpeg (Mac) or sudo apt install ffmpeg (Linux)"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# ─────────────────────────────────────────────
# 6. ffprobe (comes with FFmpeg)
# ─────────────────────────────────────────────
echo "Checking ffprobe..."
if command -v ffprobe &>/dev/null; then
    ok "ffprobe available"
else
    fail "ffprobe — should come with ffmpeg. Reinstall ffmpeg."
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ─────────────────────────────────────────────
# 7. yt-dlp (system-level)
# ─────────────────────────────────────────────
echo "Checking yt-dlp..."
if command -v yt-dlp &>/dev/null; then
    ok "yt-dlp available"
else
    info "Installing yt-dlp..."
    if [[ "$OS" == "mac" ]]; then
        brew install yt-dlp
    elif [[ "$OS" == "linux" ]]; then
        pip3 install yt-dlp 2>/dev/null || sudo apt install -y yt-dlp 2>/dev/null
    fi
    if command -v yt-dlp &>/dev/null; then
        ok "yt-dlp installed"
    else
        fail "yt-dlp — try: pip3 install yt-dlp"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# ─────────────────────────────────────────────
# 8. Python packages (requirements.txt)
# ─────────────────────────────────────────────
echo "Installing Python packages..."
if [[ -f requirements.txt ]]; then
    pip3 install -r requirements.txt 2>&1 | tail -1
    # Verify each package
    ALL_OK=true
    for pkg in "cv2:opencv-python" "numpy:numpy" "PIL:Pillow" "yt_dlp:yt-dlp"; do
        MODULE="${pkg%%:*}"
        NAME="${pkg##*:}"
        if python3 -c "import $MODULE" 2>/dev/null; then
            ok "$NAME"
        else
            fail "$NAME — try: pip3 install $NAME"
            ERRORS=$((ERRORS + 1))
            ALL_OK=false
        fi
    done
else
    fail "requirements.txt not found — make sure you're in the yt-to-shorts folder"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ─────────────────────────────────────────────
# 9. Fonts
# ─────────────────────────────────────────────
echo "Checking fonts..."
if [[ -f fonts/Montserrat-Bold.ttf && -f fonts/Montserrat-ExtraBold.ttf ]]; then
    ok "Montserrat fonts (Bold + ExtraBold)"
else
    fail "Montserrat fonts missing from fonts/ folder — re-extract the ZIP"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ─────────────────────────────────────────────
# 10. .env file
# ─────────────────────────────────────────────
echo "Checking .env configuration..."
if [[ -f .env ]]; then
    if grep -q "GATHOS_IMAGE_API_KEY=img_" .env 2>/dev/null; then
        ok ".env file with API key configured"
    elif grep -q "GATHOS_IMAGE_API_KEY=$" .env 2>/dev/null || grep -q "GATHOS_IMAGE_API_KEY=your" .env 2>/dev/null || grep -q "GATHOS_IMAGE_API_KEY=$" .env 2>/dev/null; then
        fail ".env exists but API key is empty — edit .env and add your Gathos key"
        ERRORS=$((ERRORS + 1))
    else
        KEY_LINE=$(grep "GATHOS_IMAGE_API_KEY" .env 2>/dev/null || echo "")
        if [[ -n "$KEY_LINE" && "$KEY_LINE" != *"="* ]] || [[ -z "$KEY_LINE" ]]; then
            fail ".env exists but GATHOS_IMAGE_API_KEY not found — edit .env"
            ERRORS=$((ERRORS + 1))
        else
            ok ".env file with API key configured"
        fi
    fi
else
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo -e "  ${YELLOW}[CREATED]${NC} .env file from template"
        echo -e "  ${RED}[ACTION NEEDED]${NC} Edit .env and add your Gathos Image API key"
        echo "    Get one at: https://gathos.com"
        ERRORS=$((ERRORS + 1))
    else
        fail ".env.example not found — make sure you're in the yt-to-shorts folder"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo "============================================"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "  ${GREEN}ALL DONE! Setup complete.${NC}"
    echo ""
    echo "  To verify:  PYTHONPATH=. python3 lib/pipeline.py --stage check"
    echo ""
    echo "  To run:     Open Claude Code in this folder and say:"
    echo "              \"Make me 5 clips from this YouTube video: [URL]\""
else
    echo -e "  ${RED}$ERRORS issue(s) need attention.${NC}"
    echo "  Fix the items marked [MISSING] above, then run this script again."
fi
echo "============================================"
echo ""
