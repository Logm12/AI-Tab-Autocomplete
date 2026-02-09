#!/bin/bash
# =====================================================
# Extract Training Package on Offline Machine
# =====================================================

IMAGE="longmac0110/ai-autocomplete-training:latest"
TARGET_DIR="/home/vt_admin/VTNET/USERS/thienln4/CODEV-EDGE/train_eval"

echo "=== AI Auto-Complete Training Package Extraction ==="
echo ""

# Step 1: Pull image
echo "Step 1: Pulling image..."
docker pull $IMAGE

# Step 2: Create temp container
echo ""
echo "Step 2: Creating temp container..."
docker create --name training_temp $IMAGE

# Step 3: Copy files
echo ""
echo "Step 3: Copying files to $TARGET_DIR..."
mkdir -p $TARGET_DIR
docker cp training_temp:/package/. $TARGET_DIR/

# Step 4: Cleanup
echo ""
echo "Step 4: Cleanup..."
docker rm training_temp

echo ""
echo "=== DONE! ==="
echo ""
echo "Files extracted to: $TARGET_DIR"
echo ""
echo "Next steps:"
echo "  conda activate thienln-edge"
echo "  cd $TARGET_DIR"
echo "  pip install --no-index --find-links=./wheels numpy==1.26.4"
echo "  pip install --no-index --find-links=./wheels -r requirements_training.txt"
echo ""
