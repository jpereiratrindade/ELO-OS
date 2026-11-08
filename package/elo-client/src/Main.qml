import QtQuick

Window {
  visible: true
  visibility: Window.FullScreen
  width: 1280
  height: 720
  color: "#101820"
  title: "ELO/OS — Demo P2"

  Column {
    anchors.centerIn: parent
    spacing: 20
    Text {
      text: "ELO/OS"
      color: "#ffffff"
      font.pixelSize: 76
      font.bold: true
      anchors.horizontalCenter: parent.horizontalCenter
    }
    Text {
      text: "READY_LOCAL · Demo Qt/QML · sem rede necessária"
      color: "#bad9e5"
      font.pixelSize: 26
      anchors.horizontalCenter: parent.horizontalCenter
    }
    Text {
      text: "Faça simples. Depois deixe mais leve."
      color: "#88aab7"
      font.pixelSize: 18
      anchors.horizontalCenter: parent.horizontalCenter
    }
  }
}
