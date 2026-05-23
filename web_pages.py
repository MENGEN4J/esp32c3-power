"""
Web 页面构建模块
职责：WiFi 配网页面 HTML 生成，与 WiFiManager 网络逻辑分离

运行环境：MicroPython v1.28
"""

import config


def build_landing_page():
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>BikePower</title>'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'body{min-height:100vh;background:linear-gradient(135deg,#fff7fa,#ffe4ec);padding:24px 16px;display:flex;justify-content:center;align-items:flex-start;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}'
            '.box{max-width:380px;width:100%;background:rgba(255,255,255,0.96);border-radius:22px;padding:26px;box-shadow:0 10px 34px rgba(214,69,96,0.16);backdrop-filter:blur(10px)}'
            'h1{color:#d64560;text-align:center;margin:0 0 6px;font-size:26px;font-weight:800;letter-spacing:-0.5px}'
            '.sub{color:#a0808a;text-align:center;margin:0 0 18px;font-size:13px;font-weight:500}'
            '.timer{background:linear-gradient(135deg,#d64560,#ec6a85);border-radius:16px;padding:18px;text-align:center;margin-bottom:20px;box-shadow:0 6px 20px rgba(214,69,96,0.35)}'
            '.timer-text{font-size:24px;font-weight:800;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.15)}'
            '.notice{background:#fff9f0;border:1px solid #f3d4a8;border-radius:12px;padding:14px;margin-bottom:20px;text-align:left}'
            '.notice p{color:#9a6a2e;font-size:13px;line-height:1.6}'
            '.btn-primary{display:block;width:100%;padding:18px;background:linear-gradient(135deg,#d64560,#ec6a85);color:#fff;border:none;border-radius:14px;font-size:18px;font-weight:700;cursor:pointer;margin-bottom:14px;text-decoration:none;text-align:center;transition:transform 0.15s,box-shadow 0.15s;box-shadow:0 4px 12px rgba(214,69,96,0.3)}'
            '.btn-primary:active{transform:scale(0.97);box-shadow:0 2px 8px rgba(214,69,96,0.25)}'
            '.btn-secondary{display:block;width:100%;padding:16px;background:#fff;color:#d64560;border:2px solid #d64560;border-radius:14px;font-size:16px;font-weight:600;cursor:pointer;text-decoration:none;text-align:center;transition:background 0.15s,transform 0.15s}'
            '.btn-secondary:active{background:#fff0f5;transform:scale(0.97)}'
            '.desc{font-size:12px;color:#b08a94;text-align:center;margin-top:8px;line-height:1.5}'
            '.warn{font-size:12px;color:#d68e45;text-align:center;margin-top:18px;line-height:1.6;padding:12px;background:#fff9f0;border-radius:10px;border:1px solid #f3d4a8}'
            '</style></head><body>'
            '<div class="box">'
            '<h1>BikePower</h1>'
            '<p class="sub">蓝牙功率 / 踏频 / 心率模拟器</p>'
            '<div class="timer"><div class="timer-text" id="cd">--秒后关闭WiFi</div></div>'
            '<div class="notice"><p>配网期间蓝牙会暂停，骑行 App 会暂时断开。配置完成或超时后设备会自动重启恢复蓝牙。</p></div>'
            '<a href="/wifi_setup" class="btn-primary">扫描 WiFi 并配网</a>'
            '<p class="desc">连接家庭 WiFi 后可检查 OTA 更新</p>'
            '<a href="/config" class="btn-secondary">只修改模拟参数</a>'
            '<p class="desc">不连接家庭 WiFi，直接设置功率/踏频/心率</p>'
            '<div class="warn">请在倒计时结束前完成操作；超时会自动重启</div>'
            '</div><script>setInterval(function(){fetch("/time").then(function(r){return r.text()}).then(function(t){var s=parseInt(t);document.getElementById("cd").textContent=s>0?s+"秒后关闭WiFi":"即将关闭"})},1000)</script></body></html>')


def build_wifi_setup_page():
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>一键配网</title>'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'body{min-height:100vh;background:linear-gradient(135deg,#fff7fa,#ffe4ec);padding:24px 16px;display:flex;justify-content:center;align-items:flex-start;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}'
            '.box{max-width:390px;width:100%;background:rgba(255,255,255,0.96);border-radius:22px;padding:26px;box-shadow:0 10px 34px rgba(214,69,96,0.16);backdrop-filter:blur(10px)}'
            'h1{color:#d64560;text-align:center;margin:0 0 18px;font-size:22px;font-weight:800;letter-spacing:-0.5px}'
            '.info-box{background:#fff5f7;border:1px solid #fcc2d0;border-radius:12px;padding:14px;margin-bottom:20px;text-align:center}'
            '.info-box p{color:#9a3447;font-size:13px;line-height:1.6}'
            '.btn{display:block;width:100%;padding:16px;border:none;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;margin-bottom:12px;text-align:center;text-decoration:none;transition:transform 0.15s,box-shadow 0.15s}'
            '.btn-pink{background:linear-gradient(135deg,#d64560,#ec6a85);color:#fff;box-shadow:0 4px 12px rgba(214,69,96,0.3)}'
            '.btn-pink:active{transform:scale(0.97);box-shadow:0 2px 8px rgba(214,69,96,0.25)}'
            '.btn-outline{background:#fff;color:#d64560;border:2px solid #d64560;transition:background 0.15s,transform 0.15s}'
            '.btn-outline:active{background:#fff0f5;transform:scale(0.97)}'
            '.loading{text-align:center;padding:40px 0}'
            '.loading .spinner{display:inline-block;width:44px;height:44px;border:4px solid #f8d7e0;border-top-color:#d64560;border-radius:50%;animation:spin 0.8s linear infinite}'
            '@keyframes spin{to{transform:rotate(360deg)}}'
            '.loading p{color:#a0808a;margin-top:16px;font-size:15px}'
            '.net-item{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #f8e8ed;cursor:pointer;transition:background 0.15s}'
            '.net-item:active{background:#fff5f7}'
            '.net-item:last-child{border-bottom:none}'
            '.net-name{font-size:15px;color:#444;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}'
            '.net-signal{font-size:12px;color:#a0808a;margin-left:10px;white-space:nowrap}'
            '.net-lock{margin-right:8px;font-size:14px}'
            '.input-group{margin-bottom:18px}'
            '.input-group label{display:block;margin-bottom:8px;color:#7a5a64;font-size:14px;font-weight:600}'
            '.input-group input{width:100%;padding:14px;border:2px solid #f0c8d4;border-radius:12px;font-size:16px;background:#fffcfd;transition:border-color 0.15s}'
            '.input-group input:focus{outline:none;border-color:#d64560}'
            '.tip{font-size:12px;color:#a0808a;line-height:1.5;margin:-8px 0 16px}'
            '.result-box{text-align:center;padding:30px 0}'
            '.result-box .icon{font-size:56px;margin-bottom:16px}'
            '.result-box h2{font-size:20px;margin-bottom:10px;font-weight:800}'
            '.result-box p{color:#8a707a;font-size:14px}'
            '.hidden{display:none!important}'
            '.back-link{display:block;text-align:center;margin-top:14px;color:#d64560;font-size:14px;text-decoration:none;font-weight:600}'
            '.back-link:hover{text-decoration:underline}'
            '</style></head><body>'
            '<div class="box">'
            '<div id="s1" class="hidden">'
            '<h1>扫描 WiFi</h1>'
            '<div class="loading"><div class="spinner"></div><p>正在扫描附近 2.4GHz WiFi...</p></div>'
            '</div>'
            '<div id="s2">'
            '<h1>选择 WiFi</h1>'
            '<div id="nets" style="max-height:300px;overflow-y:auto;border:2px solid #f8e8ed;border-radius:12px;margin-bottom:16px;background:#fffcfd"></div>'
            '<button class="btn btn-outline" onclick="scanAgain()">重新扫描</button>'
            '<a href="/" class="back-link">返回首页</a>'
            '</div>'
            '<div id="s3" class="hidden">'
            '<h1>输入密码</h1>'
            '<div style="background:#fff5f7;border:1px solid #fcc2d0;border-radius:12px;padding:14px;margin-bottom:18px;text-align:center">'
            '<p style="color:#9a3447;font-size:16px;font-weight:700" id="sel-ssid"></p>'
            '</div>'
            '<div class="input-group"><label>WiFi 密码</label><input type="password" id="pwd" placeholder="无密码网络可留空"></div>'
            '<p class="tip">密码只保存在设备本地，用于后续 OTA 检查；输入错误可返回重新选择网络。</p>'
            '<button class="btn btn-pink" onclick="connect()">连接</button>'
            '<a href="#" onclick="showList();return false" class="back-link">返回选择其他WiFi</a>'
            '</div>'
            '<div id="s4" class="hidden">'
            '<h1>正在连接</h1>'
            '<div class="loading"><div class="spinner"></div><p>正在验证WiFi密码并连接...</p></div>'
            '</div>'
            '<div id="s5" class="hidden">'
            '<div class="result-box">'
            '<div class="icon" style="color:#d64560">&#10004;</div>'
            '<h2 style="color:#d64560">连接成功!</h2>'
            '<p id="conn-ip"></p>'
            '<p style="margin-top:14px">即将跳转到配置页面...</p>'
            '</div>'
            '</div>'
            '<div id="s6" class="hidden">'
            '<div class="result-box">'
            '<div class="icon" style="color:#e66e7c">&#10008;</div>'
            '<h2 style="color:#e66e7c">连接失败</h2>'
            '<p id="err-msg" style="color:#e66e7c"></p>'
            '</div>'
            '<button class="btn btn-outline" onclick="showList()">重新选择</button>'
            '</div>'
            '<div class="info-box"><p>配网期间蓝牙暂停，完成后会自动重启恢复蓝牙。</p></div>'
            '</div>'
            '<script>'
            'var ssid="";'
            'function show(id){["s1","s2","s3","s4","s5","s6"].forEach(function(x){document.getElementById(x).classList.add("hidden")});document.getElementById(id).classList.remove("hidden")}'
            'function scan(){show("s1");fetch("/scan").then(function(r){return r.json()}).then(function(d){if(d.error){alert(d.error);return}if(d.status==="scanning"){setTimeout(pollScan,500);return}renderNets(d);show("s2")}).catch(function(e){alert("扫描失败: "+e)})}'
            'function pollScan(){fetch("/scan").then(function(r){return r.json()}).then(function(d){if(d.status==="scanning"){setTimeout(pollScan,500)}else{renderNets(d);show("s2")}}).catch(function(e){setTimeout(pollScan,1000)})}'
            'function renderNets(d){var h="";d.forEach(function(n){var bars=n.rssi>-50?4:n.rssi>-60?3:n.rssi>-70?2:1;var barStr="";for(var i=0;i<4;i++){barStr+=\'<span style="display:inline-block;width:5px;height:\'+(10+i*5)+\'px;background:\'+(i<bars?"#d64560":"#f0c8d4")+\';margin:0 1.5px;border-radius:2px;vertical-align:bottom"></span>\'}var lock=n.enc?\'<span class="net-lock">&#128274;</span>\':\'<span class="net-lock">&#128275;</span>\';h+=\'<div class="net-item" onclick="selectNet(this)" data-ssid="\'+n.ssid.replace(/"/g,"&quot;")+\'">\'+lock+\'<span class="net-name">\'+n.ssid+\'</span><span class="net-signal">\'+barStr+" "+n.rssi+\'dBm</span></div>\'});if(!h)h=\'<p style="text-align:center;color:#a0808a;padding:24px;font-size:14px">未发现WiFi网络</p>\';document.getElementById("nets").innerHTML=h}'
            'function scanAgain(){scan()}'
            'function selectNet(el){ssid=el.getAttribute("data-ssid");document.getElementById("sel-ssid").textContent=ssid;document.getElementById("pwd").value="";show("s3")}'
            'function showList(){show("s2")}'
            'function connect(){var pwd=document.getElementById("pwd").value;if(!ssid){alert("未选择WiFi");return}show("s4");fetch("/wifi_connect",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"ssid="+encodeURIComponent(ssid)+"&password="+encodeURIComponent(pwd)}).then(function(r){return r.json()}).then(function(d){if(d.ok){if(d.msg==="already_connected"){document.getElementById("conn-ip").textContent="IP: "+d.ip;show("s5");setTimeout(function(){location.href="/config"},2000)}else{pollStatus()}}else{document.getElementById("err-msg").textContent=d.msg||"连接失败";show("s6")}}).catch(function(e){alert("请求失败: "+e);show("s3")})}'
            'function pollStatus(){fetch("/wifi_status").then(function(r){return r.json()}).then(function(d){if(d.status==="connecting"){setTimeout(pollStatus,1000)}else if(d.status==="connected"){document.getElementById("conn-ip").textContent="IP: "+d.ip;show("s5");setTimeout(function(){location.href="/config"},2000)}else if(d.status==="failed"){document.getElementById("err-msg").textContent=d.msg||"连接失败";show("s6")}else{document.getElementById("err-msg").textContent="未知状态";show("s6")}}).catch(function(e){setTimeout(pollStatus,2000)})}'
            'scan();'
            '</script></body></html>')


def _mode_checked(current_mode, mode):
    return ' checked' if current_mode == mode else ''


def _mode_name(mode):
    if mode == config.RIDE_MODE_ROAD:
        return "真实路骑"
    if mode == config.RIDE_MODE_INTERVAL:
        return "间歇训练"
    if mode == config.RIDE_MODE_RANDOM:
        return "随机巡航"
    return "固定功率"


def build_config_page(power_val, cadence_val, hr_val, mode_val=None, wifi_configured=False, ota_info=None, current_version=""):
    if mode_val not in config.RIDE_MODES:
        mode_val = config.DEFAULT_RIDE_MODE
    manual_disabled = ' disabled' if mode_val != config.RIDE_MODE_STEADY else ''
    wifi_info = ""
    if wifi_configured:
        wifi_info = '<div class="wifi-card wifi-ok"><span>&#10004; WiFi 已连接，可检查 OTA 更新</span></div>'
    else:
        wifi_info = '<div class="wifi-card"><span>需要 OTA 更新时，再连接家庭 WiFi</span><a href="/wifi_setup">去配网</a></div>'

    top_action = ''
    if wifi_configured:
        top_action = '<a class="setup-link" href="/wifi_setup">配网 / OTA</a>'

    ota_section = ""
    if ota_info and ota_info.get('has_update'):
        version = ota_info.get('version', '')
        changelog = ota_info.get('changelog', '')
        ota_section = ('<div style="background:#f0fff4;border:1px solid #bfe8cc;border-radius:14px;padding:16px;margin-bottom:18px">'
                       '<div style="display:flex;align-items:center;margin-bottom:10px">'
                       '<span style="font-size:20px;color:#2f9e55;margin-right:10px">&#11014;</span>'
                       '<span style="color:#2f7d46;font-size:16px;font-weight:800">发现新版本 v' + version + '</span>'
                       '</div>'
                       '<p style="color:#2f7d46;font-size:13px;margin-bottom:14px;line-height:1.5">' + changelog + '</p>'
                       '<button type="button" onclick="startUpdate()" style="width:100%;padding:14px;background:linear-gradient(135deg,#2f9e55,#40c878);color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;box-shadow:0 4px 12px rgba(47,158,85,0.28);transition:transform 0.15s,box-shadow 0.15s">立即更新</button>'
                       '</div>')
    elif ota_info and not ota_info.get('has_update') and not ota_info.get('error'):
        ota_section = '<div style="background:#f8f8f8;border:1px solid #e8e8e8;border-radius:10px;padding:12px;margin-bottom:16px;text-align:center"><span style="color:#8a707a;font-size:13px;font-weight:600">&#10004; 当前已是最新版本 v' + current_version + '</span></div>'
    elif ota_info and ota_info.get('error'):
        ota_section = '<div style="background:#fff9f0;border:1px solid #f3d4a8;border-radius:10px;padding:12px;margin-bottom:16px;text-align:center"><span style="color:#d68e45;font-size:13px;font-weight:600">' + ota_info.get('error', '') + '</span></div>'
    elif wifi_configured and ota_info and ota_info.get('status') == 'checking':
        ota_section = '<div id="ota-banner" style="background:#fff5f7;border:1px solid #fcc2d0;border-radius:10px;padding:12px;margin-bottom:16px;text-align:center"><span style="color:#9a3447;font-size:13px;font-weight:600">&#8987; 正在检查更新...</span></div>'
    elif not wifi_configured:
        ota_section = ''

    bt_note = '<div class="soft-note">当前处于配置模式，蓝牙会暂时暂停；保存后设备会自动重启并恢复蓝牙。</div>'

    version_line = '<div style="font-size:12px;color:#a0808a;text-align:center;margin-top:12px;font-weight:500">当前版本: v' + current_version + '</div>'

    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>BikePower 配置</title>'
            '<style>*{margin:0;padding:0;box-sizing:border-box}'
            'body{min-height:100vh;background:linear-gradient(135deg,#fff7fa,#ffe4ec);padding:18px 14px;display:flex;justify-content:center;align-items:flex-start;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}'
            '.box{max-width:390px;width:100%;background:rgba(255,255,255,0.97);border-radius:24px;padding:22px;box-shadow:0 10px 34px rgba(214,69,96,0.16);backdrop-filter:blur(10px)}'
            '.topbar{display:flex;flex-direction:column;align-items:center;gap:10px;margin-bottom:14px;text-align:center}'
            '.brand{min-width:0;width:100%}.eyebrow{color:#d64560;font-size:12px;font-weight:800;letter-spacing:.4px;margin-bottom:4px}'
            'h1{color:#3d2a30;margin:0;font-size:24px;font-weight:850;letter-spacing:-0.5px}'
            '.sub{color:#a0808a;font-size:13px;line-height:1.5;margin-top:6px;text-align:center}'
            '.setup-link{display:inline-flex;align-items:center;justify-content:center;color:#d64560;background:#fff5f7;border:1px solid #fcc2d0;border-radius:999px;padding:9px 16px;font-size:12px;font-weight:800;text-decoration:none;box-shadow:0 4px 12px rgba(214,69,96,0.08)}'
            '.timer{background:linear-gradient(135deg,#d64560,#ec6a85);border-radius:16px;padding:14px;text-align:center;margin-bottom:14px;box-shadow:0 6px 18px rgba(214,69,96,0.28)}'
            '.timer-text{font-size:21px;font-weight:800;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.15)}'
            '.wifi-card{display:flex;justify-content:space-between;align-items:center;gap:12px;background:#fff7fa;border:1px solid #f8d7e0;border-radius:14px;padding:12px 14px;margin-bottom:14px}'
            '.wifi-card span{color:#8a5a68;font-size:13px;font-weight:650;line-height:1.5}.wifi-card a{color:#d64560;font-size:12px;font-weight:800;text-decoration:none;white-space:nowrap}'
            '.wifi-ok{background:#f0fff4;border-color:#c5e8d2}.wifi-ok span{color:#3d8a5a}'
            '.soft-note{background:#fff9f0;border:1px solid #f3d4a8;border-radius:12px;padding:12px 14px;margin-bottom:16px;color:#9a6a2e;font-size:13px;font-weight:600;line-height:1.55}'
            '.form-card{background:#fffcfd;border:1px solid #f8e8ed;border-radius:18px;padding:16px;margin-top:12px}'
            '.mode-grid{display:grid;grid-template-columns:1fr;gap:10px;margin:10px 0 6px}'
            '.mode-card{display:block;border:2px solid #f0c8d4;border-radius:14px;padding:12px;background:#fff;cursor:pointer}'
            '.mode-card input{width:auto;margin-right:8px;vertical-align:middle}'
            '.mode-title{color:#3d2a30;font-size:14px;font-weight:800}'
            '.mode-desc{display:block;color:#a0808a;font-size:12px;line-height:1.45;margin:6px 0 0 24px;font-weight:500}'
            'label{display:block;margin:14px 0 8px;color:#7a5a64;font-size:14px;font-weight:700}'
            'label:first-child{margin-top:0}'
            'input[type=number]{width:100%;padding:15px;border:2px solid #f0c8d4;border-radius:14px;font-size:18px;background:#fff;transition:border-color 0.15s,box-shadow 0.15s;font-weight:650;color:#3d2a30}'
            'input[type=number]:focus{outline:none;border-color:#d64560;box-shadow:0 0 0 3px rgba(214,69,96,.10)}'
            'input:disabled{background:#f8f1f4;color:#a0808a;border-color:#ead4dc}'
            '.manual-note{font-size:12px;color:#9a6a2e;background:#fff9f0;border:1px solid #f3d4a8;border-radius:10px;padding:10px;margin:12px 0 2px;line-height:1.5}'
            'button{width:100%;padding:17px;background:linear-gradient(135deg,#d64560,#ec6a85);color:#fff;border:none;border-radius:14px;font-size:17px;font-weight:800;margin-top:20px;cursor:pointer;box-shadow:0 4px 12px rgba(214,69,96,0.3);transition:transform 0.15s,box-shadow 0.15s}'
            'button:active{transform:scale(0.97);box-shadow:0 2px 8px rgba(214,69,96,0.25)}'
            '.note{font-size:12px;color:#a0808a;text-align:center;margin-top:14px;line-height:1.5;font-weight:500}'
            '.back-link{display:block;text-align:center;margin-top:14px;color:#d64560;font-size:13px;text-decoration:none;font-weight:700}'
            '.back-link:hover{text-decoration:underline}'
            '</style></head><body>'
            '<div class="box">'
            '<div class="topbar"><div class="brand"><div class="eyebrow">BIKEPOWER</div><h1>调整模拟数据</h1><div class="sub">修改骑行 App 看到的功率、踏频和心率</div></div>' + top_action + '</div>'
            '<div class="timer"><div class="timer-text" id="cd">--秒后关闭WiFi</div></div>'
            + wifi_info + ota_section + bt_note +
            '<form class="form-card" method="POST" action="/config">'
            '<label>骑行模式</label>'
            '<div class="mode-grid">'
            '<label class="mode-card"><input type="radio" name="mode" onchange="syncMode()" value="' + config.RIDE_MODE_STEADY + '"' + _mode_checked(mode_val, config.RIDE_MODE_STEADY) + '><span class="mode-title">固定功率</span><span class="mode-desc">使用下方功率、踏频、心率表单，稳定小幅波动。</span></label>'
            '<label class="mode-card"><input type="radio" name="mode" onchange="syncMode()" value="' + config.RIDE_MODE_ROAD + '"' + _mode_checked(mode_val, config.RIDE_MODE_ROAD) + '><span class="mode-title">真实路骑</span><span class="mode-desc">内置滑行、巡航、爬坡、冲刺、恢复曲线，不使用表单数值。</span></label>'
            '<label class="mode-card"><input type="radio" name="mode" onchange="syncMode()" value="' + config.RIDE_MODE_INTERVAL + '"' + _mode_checked(mode_val, config.RIDE_MODE_INTERVAL) + '><span class="mode-title">间歇训练</span><span class="mode-desc">内置 60 秒高强度 + 120 秒恢复，不使用表单数值。</span></label>'
            '<label class="mode-card"><input type="radio" name="mode" onchange="syncMode()" value="' + config.RIDE_MODE_RANDOM + '"' + _mode_checked(mode_val, config.RIDE_MODE_RANDOM) + '><span class="mode-title">随机巡航</span><span class="mode-desc">内置 80-260W 随机游走，不使用表单数值。</span></label>'
            '</div>'
            '<div class="manual-note" id="mode-note">只有固定功率模式会使用下方表单数值；其他模式使用设备内置曲线。</div>'
            '<label>功率(W) <span style="color:#a0808a;font-weight:500">0-2000</span></label><input id="power-input" inputmode="numeric" type="number" name="power" value="' + str(power_val) + '" min="0" max="2000"' + manual_disabled + '>'
            '<label>踏频(RPM) <span style="color:#a0808a;font-weight:500">20-120</span></label><input id="cadence-input" inputmode="numeric" type="number" name="cadence" value="' + str(cadence_val) + '" min="20" max="120"' + manual_disabled + '>'
            '<label>心率(BPM) <span style="color:#a0808a;font-weight:500">60-200</span></label><input id="heartrate-input" inputmode="numeric" type="number" name="heartrate" value="' + str(hr_val) + '" min="60" max="200"' + manual_disabled + '>'
            '<button type="submit">保存并重启</button></form>'
            '<div class="note">保存后约 5 秒重启；回到骑行 App 重新连接 BikePower 即可生效</div>'
            + version_line +
            '</div><script>'
            'function syncMode(){var m=document.querySelector("input[name=mode]:checked").value;var on=m==="steady";["power-input","cadence-input","heartrate-input"].forEach(function(id){document.getElementById(id).disabled=!on});document.getElementById("mode-note").textContent=on?"固定功率模式会使用下方表单数值。":"当前模式使用设备内置曲线，下方数值不会生效。"}syncMode();'
            'function startUpdate(){fetch("/start_update",{method:"POST"}).then(function(r){return r.json()}).then(function(d){if(d.ok){location.href="/update_page"}else{alert(d.msg)}}).catch(function(e){alert("请求失败: "+e)})}'
            'function pollOta(){var b=document.getElementById("ota-banner");if(!b)return;fetch("/check_update").then(function(r){return r.json()}).then(function(d){if(d.has_update){b.style.background="#f0fff4";b.style.borderColor="#bfe8cc";b.innerHTML=\'<span style="color:#2f7d46;font-size:13px;font-weight:600">&#11014; 发现新版本 v\'+d.version+\'</span><br><button onclick=\\\'startUpdate()\\\' style=\\\'margin-top:12px;padding:12px;background:linear-gradient(135deg,#2f9e55,#40c878);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer\\\'>立即更新</button>\'}else if(d.has_update===false){b.style.background="#f8f8f8";b.style.borderColor="#e8e8e8";b.innerHTML=\'<span style="color:#8a707a;font-size:13px;font-weight:600">&#10004; 当前已是最新版本</span>\'}else if(d.error){b.style.background="#fff9f0";b.style.borderColor="#f3d4a8";b.innerHTML=\'<span style="color:#d68e45;font-size:13px;font-weight:600">\'+d.error+\'</span>\'}}).catch(function(){})}'
            'setTimeout(pollOta,3000);setInterval(pollOta,10000);'
            'setInterval(function(){fetch("/time").then(function(r){return r.text()}).then(function(t){var s=parseInt(t);document.getElementById("cd").textContent=s>0?s+"秒后关闭WiFi":"即将关闭"})},1000)'
            '</script></body></html>')


def build_success_page(power_val, cadence_val, hr_val, mode_val=None):
    if mode_val not in config.RIDE_MODES:
        mode_val = config.DEFAULT_RIDE_MODE
    return ('<!DOCTYPE html>'
            '<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>设置已保存</title>'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'body{min-height:100vh;background:linear-gradient(135deg,#fff7fa,#ffe4ec);padding:24px 16px;display:flex;justify-content:center;align-items:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}'
            '.box{max-width:340px;width:100%;background:rgba(255,255,255,0.95);border-radius:20px;padding:32px;text-align:center;box-shadow:0 8px 32px rgba(214,69,96,0.15);backdrop-filter:blur(10px)}'
            '.icon{font-size:52px;color:#d64560;margin-bottom:14px}'
            'h1{color:#d64560;font-size:20px;margin-bottom:18px;font-weight:800;letter-spacing:-0.5px}'
            '.values{background:#fff5f7;border-radius:12px;padding:16px;margin:16px 0;border:1px solid #fcc2d0}'
            '.values p{color:#9a3447;font-size:15px;font-weight:700}'
            '.reboot-box{background:linear-gradient(135deg,#d64560,#ec6a85);border-radius:14px;padding:18px;margin:20px 0;color:#fff;box-shadow:0 4px 12px rgba(214,69,96,0.3)}'
            '.reboot-box .title{font-size:16px;font-weight:800;margin-bottom:8px}'
            '.reboot-box .desc{font-size:13px;opacity:0.95;line-height:1.6}'
            '.countdown{background:#fff;border:3px solid #d64560;color:#d64560;font-size:48px;font-weight:800;padding:14px;border-radius:50%;width:88px;height:88px;display:flex;justify-content:center;align-items:center;margin:18px auto;animation:pulse 1s infinite}'
            '@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}'
            '.note{font-size:12px;color:#a0808a;margin-top:14px;font-weight:500}'
            '</style></head><body>'
            '<div class="box">'
            '<div class="icon">&#10004;</div>'
            '<h1>配置已保存</h1>'
            '<div class="values">'
            '<p>' + str(power_val) + 'W / ' + str(cadence_val) + 'RPM / ' + str(hr_val) + 'BPM</p>'
            '<p style="margin-top:8px">' + _mode_name(mode_val) + '模式</p>'
            '</div>'
            '<div class="reboot-box">'
            '<div class="title">即将重启并恢复蓝牙</div>'
            '<div class="desc">重启后请回到骑行 App<br>重新连接 BikePower</div>'
            '</div>'
            '<div class="countdown" id="t">5</div>'
            '<p class="note">倒计时结束前请保持设备供电</p>'
            '</div>'
            '<script>var t=5;function c(){if(t>0){document.getElementById("t").innerHTML=t;t--;setTimeout(c,1000)}else{document.body.innerHTML=\'<div style="text-align:center;padding:40px;color:#a0808a;font-weight:500"><p style="font-size:20px;font-weight:700;color:#d64560">设备正在重启...</p><p style="margin-top:12px;font-size:15px">请等待蓝牙恢复后重新连接</p></div>\'}}c()</script></body></html>')


def _format_size_text(size_bytes):
    try:
        size = int(size_bytes or 0)
    except (TypeError, ValueError):
        size = 0
    if size >= 1024 * 1024:
        size_mb = size / (1024.0 * 1024.0)
        if size_mb >= 10:
            return '%d MB' % int(size_mb + 0.5)
        return '%.1f MB' % size_mb
    if size >= 1024:
        return '%d KB' % int((size + 1023) / 1024)
    return '%d B' % size


def build_update_page(preview_state=None):
    completed = 0
    total = 0
    percent = 0
    downloaded_bytes = 0
    total_bytes = 0
    if preview_state:
        completed = int(preview_state.get('completed', 0))
        total = int(preview_state.get('total', 0))
        percent = int(preview_state.get('percent', 0))
        downloaded_bytes = int(preview_state.get('downloaded_bytes', 0))
        total_bytes = int(preview_state.get('total_bytes', 0))
    if total > 0:
        summary_text = '已完成 %d/%d 个文件' % (completed, total)
    else:
        summary_text = '正在准备下载...'
    if total_bytes > 0:
        detail_text = '已下载 %s / %s · %d%%' % (
            _format_size_text(downloaded_bytes),
            _format_size_text(total_bytes),
            percent
        )
    else:
        detail_text = '正在统计更新大小'
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>固件更新</title>'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'body{min-height:100vh;background:linear-gradient(135deg,#f0fff4,#e6fcf5);padding:24px 16px;display:flex;justify-content:center;align-items:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}'
            '.box{max-width:360px;width:100%;background:rgba(255,255,255,0.95);border-radius:20px;padding:30px;box-shadow:0 8px 32px rgba(214,69,96,0.15);backdrop-filter:blur(10px)}'
            'h1{color:#2f9e55;text-align:center;margin:0 0 22px;font-size:22px;font-weight:800;letter-spacing:-0.5px}'
            '.progress-box{background:#f0fff4;border-radius:14px;padding:24px;margin-bottom:18px;text-align:center;border:1px solid #bfe8cc}'
            '.progress-box .spinner{display:inline-block;width:48px;height:48px;border:4px solid #d8f5df;border-top-color:#2f9e55;border-radius:50%;animation:spin 0.8s linear infinite}'
            '@keyframes spin{to{transform:rotate(360deg)}}'
            '.progress-box p{color:#2f7d46;margin-top:16px;font-size:15px;font-weight:600}'
            '.progress-bar{background:#d8f5df;border-radius:10px;height:22px;margin:16px 0;overflow:hidden;border:1px solid #bfe8cc}'
            '.progress-fill{background:linear-gradient(135deg,#2f9e55,#40c878);height:100%;border-radius:10px;transition:width 0.3s}'
            '.progress-text{font-size:13px;color:#a0808a;margin-top:10px;font-weight:500}'
            '.warn-box{background:#fff9f0;border:1px solid #f3d4a8;border-radius:12px;padding:14px;text-align:center}'
            '.warn-box p{color:#d68e45;font-size:13px;line-height:1.6;font-weight:600}'
            '.error-box{background:#ffeef0;border:1px solid #f8b9c4;border-radius:12px;padding:18px;text-align:center;margin-bottom:16px}'
            '.error-box h2{color:#e66e7c;font-size:17px;margin-bottom:10px;font-weight:800}'
            '.error-box p{color:#e66e7c;font-size:14px}'
            '.btn{display:block;width:100%;padding:16px;border:none;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;margin-bottom:12px;text-align:center;text-decoration:none;transition:transform 0.15s,box-shadow 0.15s}'
            '.btn-pink{background:linear-gradient(135deg,#2f9e55,#40c878);color:#fff;box-shadow:0 4px 12px rgba(47,158,85,0.28)}'
            '.btn-pink:active{transform:scale(0.97);box-shadow:0 2px 8px rgba(214,69,96,0.25)}'
            '.btn-outline{background:#fff;color:#2f9e55;border:2px solid #2f9e55;transition:background 0.15s,transform 0.15s}'
            '.btn-outline:active{background:#f0fff4;transform:scale(0.97)}'
            '.hidden{display:none!important}'
            '</style></head><body>'
            '<div class="box">'
            '<div id="downloading">'
            '<h1>固件更新中</h1>'
            '<div class="progress-box">'
            '<div class="spinner" id="spinner"></div>'
            '<p id="dl-text">' + summary_text + '</p>'
            '<div class="progress-bar"><div class="progress-fill" id="bar" style="width:' + str(percent) + '%"></div></div>'
            '<p class="progress-text" id="dl-detail">' + detail_text + '</p>'
            '</div>'
            '</div>'
            '<div id="done" class="hidden">'
            '<h1>更新完成</h1>'
            '<div class="progress-box">'
            '<p style="font-size:48px;color:#2f9e55">&#10004;</p>'
            '<p style="margin-top:14px;color:#2f7d46;font-weight:600;font-size:15px">更新完成，设备即将重启...</p>'
            '</div>'
            '</div>'
            '<div id="failed" class="hidden">'
            '<h1>更新失败</h1>'
            '<div class="error-box">'
            '<h2>&#10008; 下载失败</h2>'
            '<p id="err-msg"></p>'
            '</div>'
            '<button class="btn btn-pink" onclick="retry()">重试</button>'
            '<a href="/config" class="btn btn-outline">返回配置页</a>'
            '</div>'
            '<div class="warn-box"><p>&#9888; 请保持设备供电并等待下载完成，更新结束后会自动重启并恢复蓝牙。</p></div>'
            '</div>'
            '<script>'
            'function formatSize(v){var n=parseInt(v||0);if(n>=1048576){var mb=Math.round(n*10/1048576)/10;return (mb>=10?Math.round(mb):mb)+" MB"}if(n>=1024){return Math.round(n/1024)+" KB"}return n+" B"}'
            'function renderDownloading(d){var completed=parseInt(d.completed||0);var total=parseInt(d.total||0);var percent=parseInt(d.percent||0);var downloaded=parseInt(d.downloaded_bytes||0);var totalBytes=parseInt(d.total_bytes||0);document.getElementById("dl-text").textContent=total>0?"已完成 "+completed+"/"+total+" 个文件":"正在准备下载...";document.getElementById("bar").style.width=(percent<0?0:(percent>100?100:percent))+"%";document.getElementById("dl-detail").textContent=totalBytes>0?"已下载 "+formatSize(downloaded)+" / "+formatSize(totalBytes)+" · "+percent+"%":"正在统计更新大小"}'
            'function poll(){fetch("/update_status").then(function(r){return r.json()}).then(function(d){'
            'if(d.status==="downloading"){'
            'renderDownloading(d);'
            '}else if(d.status==="done"){'
            'document.getElementById("downloading").classList.add("hidden");'
            'document.getElementById("done").classList.remove("hidden");'
            'setTimeout(function(){document.body.innerHTML=\'<div style="text-align:center;padding:40px;color:#2f7d46;font-weight:500"><p style="font-size:20px;font-weight:700;color:#2f9e55">设备正在重启...</p><p style="margin-top:12px;font-size:15px">请等待蓝牙恢复后重新连接</p></div>\'},3000);'
            '}else if(d.status==="failed"){'
            'document.getElementById("downloading").classList.add("hidden");'
            'document.getElementById("failed").classList.remove("hidden");'
            'document.getElementById("err-msg").textContent=d.msg||"未知错误";'
            '}'
            '}).catch(function(e){})}'
            'poll();setInterval(poll,1000);'
            'function retry(){fetch("/start_update",{method:"POST"}).then(function(r){return r.json()}).then(function(d){if(d.ok){document.getElementById("downloading").classList.remove("hidden");document.getElementById("failed").classList.add("hidden");renderDownloading({completed:0,total:0,percent:0,downloaded_bytes:0,total_bytes:0})}else{alert(d.msg)}}).catch(function(e){alert("请求失败: "+e)})}'
            '</script></body></html>')
