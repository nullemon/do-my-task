import sys, time
from lib import *
img = np.zeros((H, W, 3), F32)
t0=time.time()
sun = norm([-0.8, 0.25, 0.35])
Mm = look_at(np.array([1.0, 0.05, 0.12]) * 10, (0, 0, 0)).T
draw_moon(img, W/2, H/2, 480, Mm, sun)
print(time.time()-t0)
t0=time.time(); draw_moon(img, 300, 300, 120, Mm, norm([0.3,0.2,0.9])); print(time.time()-t0)
cv2.imwrite(SCR+"/chk/moon_test.jpg", to8(bloom(img))[..., ::-1])
