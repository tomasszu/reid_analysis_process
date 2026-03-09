import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from license_plate_detection.lpr_annotator import MIN_CHAR_SCORE

# OCR confusion map
OCR_CONFUSIONS = {
    "0": ["O"], "O": ["0"],
    "1": ["I", "L"], "I": ["1", "L"], "L": ["1", "I"],
    "2": ["Z"], "Z": ["2"],
    "5": ["S"], "S": ["5"],
    "6": ["G"], "G": ["6"],
    "8": ["B"], "B": ["8"],
}


def weighted_edit_distance(plate1, scores1, plate2, scores2, blank_threshold=MIN_CHAR_SCORE):
    len1, len2 = len(plate1), len(plate2)
    dp = np.zeros((len1 + 1, len2 + 1))

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            c1, c2 = plate1[i-1], plate2[j-1]
            s1 = scores1[i-1] if i-1 < len(scores1) else 0.0
            s2 = scores2[j-1] if j-1 < len(scores2) else 0.0

            if c1 == "_" or c2 == "_":
                # Penalize blanks based on confidence exceeding threshold
                conf1 = s1 if c1 == "_" else 1.0
                conf2 = s2 if c2 == "_" else 1.0
                cost = max(0.0, min(conf1, conf2) - blank_threshold)
            else:
                # normal char mismatch
                cost = (1 - min(s1, s2)) if c1 != c2 else 0.0

            dp[i][j] = min(
                dp[i-1][j] + 1,        # deletion
                dp[i][j-1] + 1,        # insertion
                dp[i-1][j-1] + cost    # substitution
            )

    max_len = max(len1, len2)
    return dp[len1][len2] / max_len


def plate_similarity_weighted(track1, track2):
    plate1, scores1 = track1["plate"], np.array(track1["char_scores"])
    plate2, scores2 = track2["plate"], np.array(track2["char_scores"])

    dist = weighted_edit_distance(plate1, scores1, plate2, scores2)
    sim = max(0.0, 1.0 - dist)  # 1 = perfect match, 0 = completely different
    return sim




def main():
    # Example track plates
    trackA = {
        "plate": "AB0123",
        "char_scores": [0.99, 0.98, 0.97, 0.95, 0.96, 0.99]
    }

    trackB = {
        "plate": "AB_1_3",  # missing character, simulating OCR uncertainty
        "char_scores": [0.99, 0.98, 0.5, 0.96, 0.42, 0.99]
    }

    trackC = {
        "plate": "A123C",  # shifted character + missing one
        "char_scores": [0.98, 0.95, 0.97, 0.94, 0.80]
    }

    trackD = {
        "plate": "BB_K__3",  # shifted character + missing one
        "char_scores": [0.72, 0.96, 0.45, 0.66, 0.40, 0.49, 61]
    }

    print("Similarity A vs A:", plate_similarity_weighted(trackA, trackA))
    print("Similarity A vs B:", plate_similarity_weighted(trackA, trackB))
    print("Similarity A vs C:", plate_similarity_weighted(trackA, trackC))
    print("Similarity B vs C:", plate_similarity_weighted(trackB, trackC))
    print("Similarity A vs D:", plate_similarity_weighted(trackA, trackD))
    print("Similarity B vs D:", plate_similarity_weighted(trackB, trackD))

    # Optional: detailed weighted edit distance
    dist = weighted_edit_distance(trackA["plate"], np.array(trackA["char_scores"]),
                                  trackB["plate"], np.array(trackB["char_scores"]))
    print("Weighted edit distance A vs B:", dist)

if __name__ == "__main__":
    main()