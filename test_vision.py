import unittest,cv2,numpy as np,base64,json
from vision import analyze
from lambda_function import handler
class VisionTest(unittest.TestCase):
    def image(self):
        image=np.full((256,256,3),220,np.uint8)
        cv2.ellipse(image,(128,128),(70,95),0,0,360,(30,150,40),-1)
        for y in range(55,210,15):cv2.line(image,(95,y),(160,y),(20,110,30),1)
        return cv2.imencode('.png',image)[1].tobytes()
    def test_leaf_region_and_lambda(self):
        raw=self.image();result=analyze(raw)
        self.assertGreater(result['green_coverage'],.25);self.assertLess(result['green_coverage'],.5)
        self.assertTrue(result['opencv_version'].startswith('5.'));self.assertTrue(result['preview'].startswith('data:image/jpeg'))
        response=handler({'body':json.dumps({'image':base64.b64encode(raw).decode()})},None)
        self.assertEqual(response['statusCode'],200)
    def test_invalid_and_dark_images(self):
        with self.assertRaises(ValueError):analyze(b'invalid')
        raw=cv2.imencode('.png',np.zeros((100,100,3),np.uint8))[1].tobytes()
        result=analyze(raw);self.assertFalse(result['quality_gate_passed']);self.assertEqual(result['green_coverage'],0)
if __name__=='__main__':unittest.main()
