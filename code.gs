// R&B Transolution — Contact Form Handler
// วิธีใช้:
// 1. สร้าง Google Sheet ใหม่ แล้วเปิด Extensions > Apps Script
// 2. วางโค้ดนี้ทับ code.gs ที่มีอยู่
// 3. รัน testSetup() ครั้งแรกเพื่อสร้าง Header
// 4. Deploy > New deployment > Web app
//    - Execute as: Me
//    - Who has access: Anyone
// 5. Copy URL ที่ได้ไปใส่ใน const APPS_SCRIPT_URL ใน index.html

const NOTIFY_EMAIL = "rnb.transolution@gmail.com";

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    sheet.appendRow([
      new Date(),
      data.name || "",
      data.phone || "",
      data.email || "",
      data.businessType || "",
      data.service || "",
      data.message || "",
      "ยังไม่ได้ติดต่อกลับ"
    ]);

    _sendNotification(data);

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    console.error(err);
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function _sendNotification(data) {
  const subject = `[Lead ใหม่] ${data.name || "ไม่ระบุชื่อ"} — ${data.service || "ไม่ระบุบริการ"}`;
  const body = [
    "มีลูกค้าใหม่ส่งข้อความผ่านเว็บไซต์ R&B Transolution",
    "",
    `ชื่อ:             ${data.name || "-"}`,
    `โทรศัพท์:        ${data.phone || "-"}`,
    `อีเมล:           ${data.email || "-"}`,
    `ประเภทธุรกิจ:    ${data.businessType || "-"}`,
    `บริการที่สนใจ:   ${data.service || "-"}`,
    `รายละเอียด:      ${data.message || "-"}`,
    "",
    `วันเวลา: ${new Date().toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}`
  ].join("\n");

  GmailApp.sendEmail(NOTIFY_EMAIL, subject, body);
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
    headerRange.setBackground("#0e7490");
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
