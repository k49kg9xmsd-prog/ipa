#!/usr/bin/env python3
import json, os, plistlib, shutil, sys, zipfile
from pathlib import Path
cfg_path, req_dir, app_dir = map(Path, sys.argv[1:4])
cfg = json.loads(cfg_path.read_text())
root = Path(__file__).resolve().parents[1]
build_dir = app_dir.parents[1]

def esc(s): return json.dumps(s or '', ensure_ascii=False)
source_mode = cfg.get('sourceMode','url')
website_url = cfg.get('websiteUrl','https://example.com')
if source_mode == 'offline':
    site_zip = req_dir/'site.zip'
    www = app_dir/'www'; www.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(site_zip) as z:
        for item in z.infolist():
            target=(www/item.filename).resolve()
            if not str(target).startswith(str(www.resolve())): raise RuntimeError('Unsafe ZIP path')
        z.extractall(www)
    if not (www/'index.html').exists():
        nested=list(www.glob('*/index.html'))
        if len(nested)==1:
            base=nested[0].parent
            for p in list(base.iterdir()): shutil.move(str(p), www/p.name)
            base.rmdir()
        else: raise RuntimeError('site.zip root must contain index.html')

splash = next(iter(req_dir.glob('splash.*')), None)
if splash: shutil.copy2(splash, app_dir/f'Splash{splash.suffix.lower()}')

orient=cfg.get('orientation','all')
portrait=['UIInterfaceOrientationPortrait','UIInterfaceOrientationPortraitUpsideDown']
landscape=['UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']
orientations = portrait if orient=='portrait' else landscape if orient=='landscape' else portrait+landscape
plist={
 'CFBundleDisplayName':cfg['appName'],'CFBundleName':cfg['appName'],'CFBundleExecutable':cfg['appName'],'CFBundleIdentifier':cfg['bundleId'],'CFBundlePackageType':'APPL',
 'CFBundleShortVersionString':cfg['version'],'CFBundleVersion':str(cfg['build']),'MinimumOSVersion':cfg['minIos'],
 'CFBundleSupportedPlatforms':['iPhoneOS'],'LSRequiresIPhoneOS':True,'UIDeviceFamily':[1,2],
 'UILaunchScreen':{},'UISupportedInterfaceOrientations':orientations,
 'UISupportedInterfaceOrientations~ipad':orientations,'UIStatusBarHidden':bool(cfg.get('fullscreen')),
 'UIViewControllerBasedStatusBarAppearance':True,'CFBundleIcons':{'CFBundlePrimaryIcon':{'CFBundleIconFiles':['AppIcon60x60'],'CFBundleIconName':'AppIcon'}},
 'CFBundleIcons~ipad':{'CFBundlePrimaryIcon':{'CFBundleIconFiles':['AppIcon60x60','AppIcon76x76'],'CFBundleIconName':'AppIcon'}}
}
if cfg.get('allowHttp'): plist['NSAppTransportSecurity']={'NSAllowsArbitraryLoads':True}
for key, field in [('NSCameraUsageDescription','cameraText'),('NSMicrophoneUsageDescription','microphoneText'),('NSPhotoLibraryUsageDescription','photosText'),('NSPhotoLibraryAddUsageDescription','photosAddText'),('NSLocationWhenInUseUsageDescription','locationText')]:
    if cfg.get(field): plist[key]=cfg[field]
with open(app_dir/'Info.plist','wb') as f: plistlib.dump(plist,f)

splash_name = f'Splash{splash.suffix.lower()}' if splash else ''
swift=f'''import UIKit
import WebKit
import UniformTypeIdentifiers

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {{
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions opts: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {{
        let w = UIWindow(frame: UIScreen.main.bounds)
        w.rootViewController = WebController()
        w.makeKeyAndVisible(); window = w
        UIApplication.shared.isIdleTimerDisabled = {str(bool(cfg.get('preventSleep'))).lower()}
        return true
    }}
}}

final class WebController: UIViewController, WKNavigationDelegate, WKUIDelegate {{
    private let web = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
    private var splash: UIView?
    override var prefersStatusBarHidden: Bool {{ {str(bool(cfg.get('fullscreen'))).lower()} }}
    override func viewDidLoad() {{
        super.viewDidLoad(); view.backgroundColor = UIColor(hex: {esc(cfg.get('splashColor','#ffffff'))})
        web.translatesAutoresizingMaskIntoConstraints = false; web.navigationDelegate = self; web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = {str(bool(cfg.get('backGesture',True))).lower()}
        {f'web.customUserAgent = {esc(cfg.get("userAgent"))}' if cfg.get('userAgent') else ''}
        view.addSubview(web); NSLayoutConstraint.activate([web.leadingAnchor.constraint(equalTo:view.leadingAnchor),web.trailingAnchor.constraint(equalTo:view.trailingAnchor),web.topAnchor.constraint(equalTo:view.topAnchor),web.bottomAnchor.constraint(equalTo:view.bottomAnchor)])
        showSplash(); loadStart()
    }}
    private func showSplash() {{
        let box=UIView(frame:view.bounds); box.autoresizingMask=[.flexibleWidth,.flexibleHeight]; box.backgroundColor=UIColor(hex:{esc(cfg.get('splashColor','#ffffff'))})
        {f'if let img=UIImage(named:{esc(splash_name)}) {{ let iv=UIImageView(image:img); iv.contentMode = .scaleAspectFit; iv.translatesAutoresizingMaskIntoConstraints=false; box.addSubview(iv); NSLayoutConstraint.activate([iv.centerXAnchor.constraint(equalTo:box.centerXAnchor),iv.centerYAnchor.constraint(equalTo:box.centerYAnchor),iv.widthAnchor.constraint(lessThanOrEqualTo:box.widthAnchor,multiplier:0.72),iv.heightAnchor.constraint(lessThanOrEqualTo:box.heightAnchor,multiplier:0.55)]) }}' if splash else ''}
        view.addSubview(box); splash=box
    }}
    private func loadStart() {{
        {'if let u=Bundle.main.url(forResource:"index",withExtension:"html",subdirectory:"www") { web.loadFileURL(u, allowingReadAccessTo:u.deletingLastPathComponent()) }' if source_mode=='offline' else f'if let u=URL(string:{esc(website_url)}) {{ web.load(URLRequest(url:u)) }}'}
    }}
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!) {{ UIView.animate(withDuration:0.25,animations:{{self.splash?.alpha=0}},completion:{{_ in self.splash?.removeFromSuperview();self.splash=nil}}) }}
    func webView(_ webView:WKWebView,decidePolicyFor action:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {{
        guard {str(bool(cfg.get('openExternal'))).lower()}, let url=action.request.url else {{ decisionHandler(.allow); return }}
        {'let homeHost = URL(string:'+esc(website_url)+')?.host; if action.navigationType == .linkActivated, url.host != homeHost { UIApplication.shared.open(url); decisionHandler(.cancel); return }' if source_mode=='url' else 'if action.navigationType == .linkActivated, ["http","https"].contains(url.scheme ?? "") { UIApplication.shared.open(url); decisionHandler(.cancel); return }'}
        decisionHandler(.allow)
    }}
    func webView(_ webView:WKWebView,createWebViewWith configuration:WKWebViewConfiguration,for navigationAction:WKNavigationAction,windowFeatures:WKWindowFeatures)->WKWebView? {{ if navigationAction.targetFrame == nil, let u=navigationAction.request.url {{ webView.load(URLRequest(url:u)) }}; return nil }}
}}
extension UIColor {{ convenience init(hex:String) {{ var s=hex.trimmingCharacters(in:.whitespacesAndNewlines); if s.hasPrefix("#"){{s.removeFirst()}}; var n:UInt64=0; Scanner(string:s).scanHexInt64(&n); self.init(red:CGFloat((n>>16)&255)/255,green:CGFloat((n>>8)&255)/255,blue:CGFloat(n&255)/255,alpha:1) }} }}
'''
(build_dir/'App.swift').write_text(swift)
(build_dir/'Assets.xcassets').mkdir(parents=True, exist_ok=True)
