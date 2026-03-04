import cv2
import numpy as np
from PIL import Image

import onnxruntime as ort

print("onnxruntime module:", ort)
print("onnxruntime file:", ort.__file__)
print("version:", getattr(ort, "__version__", "NO VERSION"))
print("dir contains SessionOptions:", "SessionOptions" in dir(ort))

def run_lpr_test(det_model, rec_model):

    try:
        im_path = "license_plate_detection/test_im/2.png"

        img = Image.open(im_path).convert("RGB")
        image = np.array(img)  # shape (H, W, 3)

        results = det_model.predict(source=image)[0]

        license_plate = results.boxes.data.tolist()[0]

        x1, y1, x2, y2, score, class_id = license_plate

        # crop license plate
        license_plate_crop = image[int(y1):int(y2), int(x1): int(x2), :]

        cv2.imshow("crop",license_plate_crop)
        cv2.waitKey(0)

        print(rec_model.run(source = license_plate_crop, return_confidence=True))
        print("LPR Models working successfully")
        return 1

    except:
        print("LPR Models NOT working.")
        return 0
    

if __name__ == "__main__":

    from ultralytics import YOLO
    from fast_plate_ocr import LicensePlateRecognizer

    onnx_providers = [
    "CUDAExecutionProvider",
    "CPUExecutionProvider",
    ]

    lpr_detection_model = YOLO('license_plate_detection/license-plate-finetune-v1l.pt')
    lpr_recognition_model = LicensePlateRecognizer('cct-xs-v1-global-model', providers=onnx_providers)
    run_lpr_test(lpr_detection_model, lpr_recognition_model)





