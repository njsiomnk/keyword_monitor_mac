import atomac
import time
bundle_name = 'com.apple.iTunes'
atomac.launchAppByBundleId(bundle_name)
appStoreRef = atomac.getAppRefByBundleId(bundle_name)
_searchTextField = appStoreRef.AXMainWindow.findFirst(AXRole='AXTextField')

x, y = _searchTextField.AXPosition
width, height = _searchTextField.AXSize
_searchTextField.AXValue = '1111'
time.sleep(5)
_searchTextField.clickMouseButtonLeft((x + width/2, y + height/2))
time.sleep(5)
_searchTextField.sendKey('<cursor_right>')
_searchTextField.sendKey('<space>')
_searchTextField.sendKey('<backspace>')
_searchTextField.sendKey('\r')

print appStoreRef.AXMainWindow.AXSize