#!/bin/bash
# Monitor Terraform Apply Progress

echo "Terraform Apply Progress Monitor"
echo "================================="
echo ""
echo "Deployment started at: $(date)"
echo ""

# Monitor the log file
if [ -f /tmp/terraform-apply.log ]; then
    echo "Latest progress:"
    echo "----------------"
    tail -20 /tmp/terraform-apply.log
    echo ""
    echo "----------------"
    
    # Count completed resources
    CREATED=$(grep -c "Creation complete" /tmp/terraform-apply.log 2>/dev/null || echo 0)
    echo "Resources created: $CREATED"
    
    # Check for errors
    ERRORS=$(grep -c "Error:" /tmp/terraform-apply.log 2>/dev/null || echo 0)
    if [ $ERRORS -gt 0 ]; then
        echo "⚠️  Errors detected: $ERRORS"
        echo ""
        echo "Error details:"
        grep "Error:" /tmp/terraform-apply.log | tail -5
    else
        echo "✓ No errors detected"
    fi
    
    # Check if completed
    if grep -q "Apply complete!" /tmp/terraform-apply.log 2>/dev/null; then
        echo ""
        echo "🎉 Deployment Complete!"
        echo ""
        grep "Apply complete!" /tmp/terraform-apply.log
    else
        echo ""
        echo "⏳ Deployment in progress..."
        echo "Run this script again to check status."
    fi
else
    echo "Log file not found. Deployment may not have started yet."
fi

echo ""
echo "To watch live:"
echo "  tail -f /tmp/terraform-apply.log"
echo ""
echo "To check Cloud SQL creation (slowest part):"
echo "  gcloud sql operations list --project=sylvan-earth-477020-u6 --limit=5"
