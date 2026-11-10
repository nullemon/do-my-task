import sys, glob, os
sys.path.insert(0, "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/12-the-moon-is-leaving/pylib")
import cv2, numpy as np
out = sys.argv[1]; cols = int(sys.argv[2]); fs = sys.argv[3:]
ims = [cv2.imread(f) for f in fs]; h, w = ims[0].shape[:2]; tw = 1900 // cols; th = int(tw * h / w)
ims = [cv2.resize(i, (tw, th), interpolation=cv2.INTER_AREA) for i in ims]
rows = [np.hstack(ims[i:i + cols] + [np.zeros_like(ims[0])] * (cols - len(ims[i:i + cols]))) for i in range(0, len(ims), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
