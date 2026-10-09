booth_set.json = list of 30 cases, each:
All image paths are relative to data/. cam_mask_overlap may be null when no tumor overlap is available (normal cases); otherwise it must be a finite number in [0, 1].
{
  "case_id": "01",
  "source_file": "malignant (12).png",
  "image": "images/case01.png",            // original, for screen
  "print_image": "print/case01_A5.png",     // upscaled + case number, for printing
  "heatmap": "heatmaps/case01.png",         // Grad-CAM overlay
  "mask_overlay": "overlays/case01.png",    // heatmap + true tumor outline
  "truth": "normal" | "benign" | "malignant",
  "ai_pred": "normal" | "benign" | "malignant",
  "ai_probs": {"normal": 0.05, "benign": 0.78, "malignant": 0.17},
  "correct": false,
  "error_type": null | "false_negative" | "false_positive" | "other_confusion",
  "cam_mask_overlap": 0.12                  // share of heatmap inside true tumor
}
false_negative = truth malignant, AI not malignant
false_positive = truth normal/benign, AI says malignant
