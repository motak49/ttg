import cv2
import depthai as dai

# Create pipeline
pipeline = dai.Pipeline()

camRgb = pipeline.create(dai.node.Camera).build()
preview = camRgb.requestOutput((1000, 500), type=dai.ImgFrame.Type.RGB888p)

# In this example we use 2 imageManips for splitting the original 1000x500
# preview frame into 2 500x500 frames
manip1 = pipeline.create(dai.node.ImageManip)
manip1.initialConfig.addCrop(0, 0, 500, 500)
preview.link(manip1.inputImage)

manip2 = pipeline.create(dai.node.ImageManip)
manip2.initialConfig.addCrop(500, 0, 500, 500)
preview.link(manip2.inputImage)

q1 = manip1.out.createOutputQueue()
q2 = manip2.out.createOutputQueue()

# depthai 3.1.0: context manager を使用
with pipeline:
    while pipeline.isRunning():
        if q1.has():
            cv2.imshow("Tile 1", q1.get().getCvFrame())

        if q2.has():
            cv2.imshow("Tile 2", q2.get().getCvFrame())

        if cv2.waitKey(1) == ord('q'):
            break