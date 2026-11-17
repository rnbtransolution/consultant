// R&B Transolution - Contact Form Handler
// วิธีใช้:
// 1. สร้าง Google Sheet ใหม่ แล้วเปิด Extensions > Apps Script
// 2. วางโค้ดนี้ทับ code.gs ที่มีอยู่
// 3. รัน testSetup() ครั้งแรกเพื่อสร้าง Header
// 4. Deploy > New deployment > Web app
//    - Execute as: Me
//    - Who has access: Anyone
// 5. Copy URL ที่ได้ไปใส่ใน const APPS_SCRIPT_URL ใน index.html
// 6. แก้โค้ดครั้งต่อไปต้อง Deploy > Manage deployments > Edit > Version: New version

const NOTIFY_EMAIL = "services@rnb-transolution.com";
const SENDER_NAME = "R&B Transolution Website";
const BRAND_NAME = "R&B Transolution";

// ตรวจสถานะ endpoint ผ่านเบราว์เซอร์
function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ status: "ready" }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  let data;

  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    console.error("อ่านข้อมูลจากฟอร์มไม่ได้: " + err.message);
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: "invalid payload" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  const lead = {
    name: _clean(data.name, 120),
    phone: _clean(data.phone, 40),
    email: _clean(data.email, 160),
    businessType: _clean(data.businessType, 120),
    service: _clean(data.service, 160),
    message: _clean(data.message, 4000)
  };

  // บันทึกลง Sheet ก่อนเสมอ ถ้าเมลล้มเหลวอย่างน้อยข้อมูลลูกค้ายังอยู่
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    sheet.appendRow([
      new Date(),
      lead.name,
      lead.phone,
      lead.email,
      lead.businessType,
      lead.service,
      lead.message,
      "ยังไม่ได้ติดต่อกลับ"
    ]);
  } catch (err) {
    console.error("บันทึกลง Sheet ไม่สำเร็จ: " + err.message);
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: "sheet write failed" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  let mailSent = true;

  try {
    _sendNotification(lead);
  } catch (err) {
    mailSent = false;
    console.error("ส่งเมลแจ้งเตือนไม่สำเร็จ: " + err.message);
  }

  return ContentService
    .createTextOutput(JSON.stringify({ status: "ok", mailSent: mailSent }))
    .setMimeType(ContentService.MimeType.JSON);
}

function _sendNotification(data) {
  const subject = "[Lead ใหม่] " +
    (data.name || "ไม่ระบุชื่อ") +
    " · " +
    (data.service || "ไม่ระบุบริการ");

  const timestamp = Utilities.formatDate(new Date(), "Asia/Bangkok", "d MMM yyyy HH:mm");
  const plain = [
    "มีลูกค้าใหม่ส่งข้อความผ่านเว็บไซต์ " + BRAND_NAME,
    "",
    "ชื่อ: " + (data.name || "-"),
    "โทรศัพท์: " + (data.phone || "-"),
    "อีเมล: " + (data.email || "-"),
    "ประเภทธุรกิจ: " + (data.businessType || "-"),
    "บริการที่สนใจ: " + (data.service || "-"),
    "",
    "รายละเอียด:",
    (data.message || "-"),
    "",
    "ส่งเมื่อ " + timestamp + " (เวลาไทย)",
    "ข้อมูลถูกบันทึกใน Google Sheet แล้ว กด Reply เพื่อตอบกลับลูกค้าโดยตรง"
  ].join("\n");

  const options = {
    name: SENDER_NAME,
    htmlBody: _buildHtml(data, timestamp)
  };

  // ให้กด Reply แล้วตอบกลับถึงลูกค้าได้เลย ถ้าลูกค้าไม่ได้กรอกอีเมลไว้ก็ไม่ต้องใส่
  if (_isEmail(data.email)) {
    options.replyTo = data.email;
  }

  GmailApp.sendEmail(NOTIFY_EMAIL, subject, plain, options);
}

function _buildHtml(data, timestamp) {
  const rows = [
    _row("ชื่อ", data.name),
    _row("โทรศัพท์", data.phone),
    _row("อีเมล", data.email),
    _row("ประเภทธุรกิจ", data.businessType),
    _row("บริการที่สนใจ", data.service),
    _row("รายละเอียด", data.message)
  ].join("");

  return '' +
    '<div style="margin:0;padding:28px 16px;background:#f0f5f7;">' +
      '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #dde7e9;border-radius:16px;">' +
        '<tr><td style="padding:22px 26px;background:#295255;border-radius:15px 15px 0 0;">' +
          '<div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#a8c6c1;">Website enquiry</div>' +
          '<div style="font-family:Georgia,\'Times New Roman\',serif;font-size:20px;color:#ffffff;padding-top:6px;">มีข้อความใหม่จากเว็บไซต์</div>' +
        '</td></tr>' +
        '<tr><td style="padding:22px 26px 8px;">' +
          '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="font-family:Arial,Helvetica,sans-serif;">' +
            rows +
          '</table>' +
        '</td></tr>' +
        '<tr><td style="padding:6px 26px 24px;">' +
          '<div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.7;color:#577877;border-top:1px solid #e6eeef;padding-top:14px;">' +
            'ส่งเมื่อ ' + _esc(timestamp) + ' (เวลาไทย)<br>' +
            'ข้อมูลถูกบันทึกใน Google Sheet แล้ว กด Reply เพื่อตอบกลับลูกค้าโดยตรง' +
          '</div>' +
        '</td></tr>' +
      '</table>' +
    '</div>';
}

function _row(label, value) {
  const text = value ? _esc(value) : "-";
  return '<tr>' +
    '<td width="140" style="padding:10px 12px 10px 0;border-bottom:1px solid #eef4f5;font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#577877;vertical-align:top;">' + _esc(label) + '</td>' +
    '<td style="padding:10px 0;border-bottom:1px solid #eef4f5;font-size:14px;line-height:1.65;color:#162623;vertical-align:top;">' + text.replace(/\n/g, "<br>") + '</td>' +
    '</tr>';
}

function _clean(value, maxLength) {
  return String(value == null ? "" : value).trim().slice(0, maxLength);
}

function _esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function _isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value || "");
}

// รันฟังก์ชันนี้ครั้งเดียวเพื่อตั้งค่า Header ใน Sheet
function testSetup() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "วันเวลา", "ชื่อ", "โทรศัพท์", "อีเมล",
      "ประเภทธุรกิจ", "บริการที่สนใจ", "รายละเอียด", "สถานะ"
    ]);

    // จัด format Header
    const headerRange = sheet.getRange(1, 1, 1, 8);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#295255");
    headerRange.setFontColor("#ffffff");
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 160);
    sheet.setColumnWidth(2, 140);
    sheet.setColumnWidth(3, 120);
    sheet.setColumnWidth(4, 200);
    sheet.setColumnWidth(5, 160);
    sheet.setColumnWidth(6, 180);
    sheet.setColumnWidth(7, 280);
    sheet.setColumnWidth(8, 140);
  }

  Logger.log("Setup complete. Sheet: " + SpreadsheetApp.getActiveSpreadsheet().getName());
}

// ทดสอบ doPost โดยไม่ต้อง deploy ก่อน
function testDoPost() {
  const mockEvent = {
    postData: {
      contents: JSON.stringify({
        name: "ทดสอบ ระบบ",
        phone: "0891234567",
        email: "test@example.com",
        businessType: "ร้านอาหาร / Restaurant",
        service: "Menu Engineering",
        message: "ต้องการปรับปรุงเมนูและเพิ่มกำไร"
      })
    }
  };

  const result = doPost(mockEvent);
  Logger.log(result.getContent());
}

// ตรวจว่าเมลแจ้งเตือนออกได้จริง โดยไม่เขียนข้อมูลลง Sheet
function testNotification() {
  _sendNotification({
    name: "ทดสอบ ระบบ",
    phone: "0891234567",
    email: "test@example.com",
    businessType: "ร้านอาหาร / Restaurant",
    service: "Menu Engineering",
    message: "ทดสอบการส่งเมลแจ้งเตือนจากเว็บไซต์"
  });

  Logger.log("ส่งเมลทดสอบไปที่ " + NOTIFY_EMAIL + " แล้ว");
}
