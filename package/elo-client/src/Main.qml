// SPDX-License-Identifier: GPL-3.0-only
import QtQuick

Window {
    id: window
    visible: true
    width: 1024
    height: 640
    minimumWidth: 640
    minimumHeight: 480
    color: "#101d23"
    title: "ELO — apresentação local"

    component LocalButton: Rectangle {
        property string label
        signal activated()
        width: 150
        height: 48
        radius: 8
        color: !enabled ? "#26363c" : activeFocus ? "#e9f6f1" : "#bdddd1"
        border.width: activeFocus ? 3 : 0
        border.color: "#52bfa1"
        activeFocusOnTab: enabled
        opacity: enabled ? 1 : 0.5
        Accessible.role: Accessible.Button
        Accessible.name: label
        Accessible.onPressAction: if (enabled) activated()
        Keys.onSpacePressed: activated()
        Keys.onReturnPressed: activated()
        Text {
            anchors.centerIn: parent
            text: parent.label
            color: parent.enabled ? "#142d27" : "#c0d0d2"
            font.pixelSize: 17
        }
        MouseArea {
            anchors.fill: parent
            onClicked: { parent.forceActiveFocus(); parent.activated() }
        }
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: Math.max(24, window.width * 0.07)
        focus: true
        Keys.onRightPressed: clientModel.next()
        Keys.onLeftPressed: clientModel.previous()
        Keys.onPressed: event => {
            if (event.key === Qt.Key_Home) {
                clientModel.reset()
                event.accepted = true
            }
        }

        Row {
            id: header
            spacing: 16
            Text { text: "ELO"; color: "#f1f6f3"; font.pixelSize: 27; font.bold: true }
            Text { text: "ELO/OS · bancada local"; color: "#a4c8bd"; font.pixelSize: 17; anchors.verticalCenter: parent.verticalCenter }
        }
        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 22
            Text {
                objectName: "pageCounter"
                text: clientModel.pageCount > 0 ? clientModel.pageNumber + " / " + clientModel.pageCount : "Sem conteúdo local"
                color: "#79c9ae"
                font.pixelSize: 18
            }
            Text {
                objectName: "pageTitle"
                text: clientModel.title
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#f1f6f3"
                font.pixelSize: window.width < 800 ? 30 : 42
                font.bold: true
            }
            Text {
                objectName: "pageBody"
                text: clientModel.body
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#c0d0d2"
                font.pixelSize: window.width < 800 ? 19 : 23
                lineHeight: 1.3
            }
        }
        Row {
            anchors.left: parent.left
            anchors.bottom: footer.top
            anchors.bottomMargin: 24
            spacing: 12
            LocalButton { objectName: "previousButton"; label: "Voltar"; enabled: clientModel.canPrevious; onActivated: clientModel.previous() }
            LocalButton { objectName: "resetButton"; label: "Recomeçar"; enabled: clientModel.pageCount > 0 && clientModel.error.length === 0; onActivated: clientModel.reset() }
            LocalButton { objectName: "nextButton"; label: "Continuar"; enabled: clientModel.canNext; onActivated: clientModel.next() }
        }
        Text {
            id: footer
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            text: clientModel.state + " · " + clientModel.fixtureLabel + "\nNo seu tempo. Sem conexão necessária."
            color: "#8da7ad"
            font.pixelSize: 15
        }
    }
}
