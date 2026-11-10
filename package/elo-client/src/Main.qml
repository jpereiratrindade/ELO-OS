// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import "MorfoTheme.js" as Theme

Window {
    id: window
    visible: true
    width: 1024
    height: 640
    minimumWidth: 640
    minimumHeight: 480
    color: Theme.background
    readonly property string uiFont: Qt.fontFamilies().indexOf("Plus Jakarta Sans") >= 0
                                     ? "Plus Jakarta Sans" : "DejaVu Sans"
    title: "ELO — experiências"
    property bool contentReady: !pageImage.visible || pageImage.status === Image.Ready

    component LocalButton: Rectangle {
        property string label
        property bool primary: false
        signal activated()
        width: 150
        height: 48
        radius: 8
        color: primary ? Theme.blue : Theme.surface
        border.width: activeFocus ? 3 : 1
        border.color: activeFocus ? Theme.focus : primary ? Theme.blue : Theme.line
        activeFocusOnTab: enabled
        opacity: enabled ? 1 : 0.45
        Accessible.role: Accessible.Button
        Accessible.name: label
        Accessible.onPressAction: if (enabled) activated()
        Keys.onSpacePressed: activated()
        Keys.onReturnPressed: activated()
        Text {
            anchors.centerIn: parent
            text: parent.label
            color: parent.primary ? Theme.surface : Theme.navy
            font.family: window.uiFont
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
            Text { text: "ELO"; font.family: window.uiFont; color: Theme.navy; font.pixelSize: 27; font.bold: true }
            Text { text: "ELO/OS · experiências"; font.family: window.uiFont; color: Theme.muted; font.pixelSize: 17; anchors.verticalCenter: parent.verticalCenter }
        }
        Rectangle {
            id: contentCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: header.bottom
            anchors.topMargin: 32
            anchors.bottom: actions.top
            anchors.bottomMargin: 24
            color: Theme.surface
            radius: 13
            border.color: Theme.line
        }
        Flickable {
            id: experience
            property string currentPage: clientModel.pageNumber + "|" + clientModel.title + "|" + clientModel.body
            onCurrentPageChanged: contentY = 0
            anchors.fill: contentCard
            anchors.margins: 24
            clip: true
            contentWidth: width
            contentHeight: contentColumn.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
        Column {
            id: contentColumn
            width: experience.width
            spacing: 22
            Text {
                objectName: "pageCounter"
                text: clientModel.pageCount > 0 ? clientModel.pageNumber + " / " + clientModel.pageCount : "Sem conteúdo local"
                color: Theme.teal
                font.family: window.uiFont
                font.pixelSize: 18
            }
            Flow {
                id: pageFlow
                width: parent.width
                spacing: 24
                readonly property bool compact: window.width < 800
                Image {
                    id: pageImage
                    objectName: "pageImage"
                    visible: clientModel.imageSource.length > 0
                    source: clientModel.imageSource
                    onSourceChanged: experience.contentY = 0
                    width: pageFlow.compact ? pageFlow.width : pageFlow.width * 0.42
                    height: visible ? Math.max(110, Math.min(240, experience.height - 50)) : 0
                    sourceSize.width: 1280
                    sourceSize.height: 720
                    fillMode: Image.PreserveAspectFit
                    cache: false
                    asynchronous: false
                    Accessible.name: clientModel.imageAlt
                }
                Column {
                    width: !pageImage.visible || pageFlow.compact ? pageFlow.width : pageFlow.width - pageImage.width - pageFlow.spacing
                    spacing: 16
                    Text {
                        objectName: "pageTitle"
                        textFormat: Text.PlainText
                        text: clientModel.title
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: Theme.navy
                        font.family: window.uiFont
                        font.pixelSize: pageImage.visible ? 32 : window.width < 800 ? 30 : 42
                        font.bold: true
                    }
                    Text {
                        objectName: "pageBody"
                        textFormat: Text.PlainText
                        text: clientModel.body
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: Theme.ink
                        font.family: window.uiFont
                        font.pixelSize: window.width < 800 ? 19 : 21
                        lineHeight: 1.3
                    }
                }
            }
        }
        }
        Rectangle {
            anchors.right: contentCard.right
            anchors.top: contentCard.top
            anchors.bottom: contentCard.bottom
            anchors.margins: 8
            width: 4
            radius: 2
            visible: experience.contentHeight > experience.height
            color: Theme.line
            Rectangle {
                width: parent.width
                height: Math.max(12, experience.visibleArea.heightRatio * parent.height)
                y: experience.visibleArea.yPosition * parent.height
                color: Theme.muted
                radius: 2
            }
        }
        Row {
            id: actions
            anchors.left: parent.left
            anchors.bottom: footer.top
            anchors.bottomMargin: 24
            spacing: 12
            LocalButton { objectName: "previousButton"; label: "Voltar"; enabled: clientModel.canPrevious; onActivated: clientModel.previous() }
            LocalButton {
                objectName: "resetButton"
                label: clientModel.canRetry ? "Tentar novamente" : "Recomeçar"
                enabled: clientModel.canRetry || (clientModel.pageCount > 0 && clientModel.error.length === 0)
                onActivated: clientModel.canRetry ? clientModel.retry() : clientModel.reset()
            }
            LocalButton { objectName: "nextButton"; primary: true; label: "Continuar"; enabled: clientModel.canNext; onActivated: clientModel.next() }
        }
        Text {
            id: footer
            anchors.right: parent.right
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            text: clientModel.state + " · " + clientModel.fixtureLabel + "\n" + clientModel.connectivity + (clientModel.contentUpdate.length > 0 ? "\n" + clientModel.contentUpdate : "") + "\nNo seu tempo. Sem conexão necessária."
            color: Theme.muted
            font.family: window.uiFont
            font.pixelSize: 15
        }
    }
}
