// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import Elo.Media 1.0
import "MorfoTheme.js" as Theme

Window {
    id: window
    visible: true
    width: 1024
    height: 640
    minimumWidth: 640
    minimumHeight: 480
    color: Theme.background
    readonly property var perception: typeof perceptionModel === "undefined" ? null : perceptionModel
    readonly property string uiFont: Qt.fontFamilies().indexOf("Plus Jakarta Sans") >= 0
                                     ? "Plus Jakarta Sans" : "DejaVu Sans"
    title: "ELO — experiências"
    property bool contentReady: (!pageImage.visible || pageImage.status === Image.Ready) && mediaPlayer.ready

    Connections {
        target: window
        function onContentReadyChanged() { Qt.callLater(experience.scheduleScroll) }
    }

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
            width: parent.width - 20
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
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
            objectName: "experienceScroll"
            property string currentPage: clientModel.exposureCycle + "|" + clientModel.pageNumber + "|" + clientModel.title + "|" + clientModel.body
            onCurrentPageChanged: Qt.callLater(scheduleScroll)
            anchors.fill: contentCard
            anchors.margins: 24
            clip: true
            contentWidth: width
            contentHeight: contentColumn.implicitHeight
            function scheduleScroll() {
                autoScroll.stop()
                contentY = 0
                if (clientModel.autoplay && window.contentReady && contentHeight > height)
                    autoScroll.start()
            }
            onContentHeightChanged: Qt.callLater(scheduleScroll)
            NumberAnimation {
                id: autoScroll
                target: experience
                property: "contentY"
                from: 0
                to: Math.max(0, experience.contentHeight - experience.height)
                duration: Math.max(1000, (clientModel.exposureSeconds - 1) * 1000)
            }
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
                MediaSurface {
                    id: mediaPlayer
                    objectName: "mediaPlayer"
                    property string playbackKey: clientModel.exposureCycle + "|" + clientModel.pageNumber + "|" + clientModel.mediaSource
                    onPlaybackKeyChanged: Qt.callLater(function() { mediaPlayer.restart() })
                    onProgressChanged: clientModel.setMediaDuration(duration)
                    kind: clientModel.mediaKind
                    source: clientModel.mediaSource
                    active: clientModel.playbackAllowed
                    width: pageFlow.compact ? pageFlow.width : pageFlow.width * 0.42
                    height: visible ? Math.max(110, Math.min(240, experience.height - 50)) : 0
                    visible: clientModel.mediaKind === "video" && clientModel.mediaSource.length > 0
                }
                Column {
                    width: (!pageImage.visible && !mediaPlayer.visible) || pageFlow.compact ? pageFlow.width : pageFlow.width - (pageImage.visible ? pageImage.width : mediaPlayer.width) - pageFlow.spacing
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
                    LocalButton {
                        objectName: "revealButton"
                        label: "Revelar"
                        primary: true
                        visible: clientModel.canReveal
                        enabled: clientModel.canReveal
                        onActivated: clientModel.reveal()
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
        Text {
            visible: mediaPlayer.error.length > 0
            text: "Mídia indisponível · " + mediaPlayer.error
            anchors.bottom: contentCard.bottom
            anchors.horizontalCenter: contentCard.horizontalCenter
            color: Theme.navy
            width: contentCard.width - 48
            wrapMode: Text.WordWrap
        }
        Text {
            anchors.top: header.bottom
            anchors.topMargin: 4
            width: parent.width
            text: window.perception ? window.perception.status : ""
            color: Theme.muted
            font.family: window.uiFont
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        Row {
            id: mediaControls
            anchors.left: parent.left
            anchors.bottom: footer.top
            anchors.bottomMargin: visible ? 12 : 0
            spacing: 8
            visible: clientModel.mediaSource.length > 0 || (window.perception && window.perception.operational && window.perception.recognitionAvailable)
            LocalButton {
                visible: clientModel.mediaSource.length > 0
                label: mediaPlayer.muted ? "Ativar som" : "Silenciar"
                onActivated: mediaPlayer.muted = !mediaPlayer.muted
            }
            LocalButton {
                visible: window.perception && window.perception.operational && window.perception.recognitionAvailable
                label: window.perception && window.perception.authorized ? "Parar reconhecimento" : "Reconhecer visitas"
                onActivated: window.perception.setAuthorized(!window.perception.authorized)
            }
            LocalButton {
                visible: window.perception && window.perception.canEnroll
                label: "Lembrar visita"
                onActivated: window.perception.enroll()
            }
            LocalButton {
                visible: window.perception && window.perception.hasCandidate
                label: window.perception && window.perception.resumePage > 0 ? "Retomar visita" : "Confirmar visita"
                onActivated: { clientModel.resumePage(window.perception.resumePage); window.perception.confirmIdentity() }
            }
            LocalButton {
                visible: window.perception && window.perception.hasProfile
                label: "Apagar cadastro"
                onActivated: window.perception.forget()
            }
        }
        Row {
            id: actions
            visible: !clientModel.autoplay
            anchors.left: parent.left
            anchors.bottom: mediaControls.visible ? mediaControls.top : footer.top
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
            text: (clientModel.autoplay ? "ELO · " + clientModel.pageNumber + " / " + clientModel.pageCount + " · " + clientModel.exposureSeconds + " s" : clientModel.state + " · " + clientModel.fixtureLabel + "\n" + clientModel.connectivity + (clientModel.contentUpdate.length > 0 ? "\n" + clientModel.contentUpdate : "") + "\nNo seu tempo. Sem conexão necessária.") + "\nSimples, leve. Sempre pronto. Sempre incompleto!"
            color: Theme.muted
            font.family: window.uiFont
            font.pixelSize: 15
        }
    }
}
