import QtQuick
import QtQuick.Controls
import QtQuick.Layouts 1.15
import QtQuick.Window

import "components"

ApplicationWindow {
    id: app
    visible: true

    width: 1210
    height: 780

    minimumWidth: 1100
    minimumHeight: 720

    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2

    title: "StemSplit AI"

    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"

    property var currentStems: []
    property int activeSection: 0
    property int procProgress: 0
    property string selectedModel: "htdemucs_6s"
    property int segmentSize: 5
    property real overlapValue: 0.25
    property int shiftsValue: 1
    property string soloStem: ""
    property var manualMutes: ({})
    property var stemWaveforms: ({})
    property var stemColors: ({})

    // --- Update state ---
    property string updateStatus: ""       // "", "checking", "available", "uptodate", "downloading", "ready", "error"
    property string updateVersion: ""
    property string updateNotes: ""
    property int updateProgress: 0

    function formatTime(sec) {
        sec = Math.floor(sec)
        var m = Math.floor(sec / 60)
        var s = sec % 60
        return m + ":" + (s < 10 ? "0" + s : s)
    }

    function activeStemLabel() {
        if (currentStems.length === 0) return ""
        if (soloStem !== "") return soloStem

        var activeCount = 0
        var activeName = ""
        for (var i = 0; i < currentStems.length; i++) {
            var name = currentStems[i].name
            if (manualMutes[name] !== true) {
                activeCount++
                activeName = name
            }
        }

        if (activeCount === 0) return "muted"
        if (activeCount === 1) return activeName
        return "mix"
    }

    function accelerationColor() {
        return backend && backend.gpuAvailable ? "#00e388" : "#FFC857"
    }

    function assignStemColors(stems) {
        var palette = [
            "#FF4D6D", "#4FC3F7", "#FFD166", "#8BE9C1",
            "#C77DFF", "#FF9F1C", "#2EC4B6", "#E76F51",
            "#A3E635", "#F472B6", "#60A5FA", "#FACC15"
        ]
        var pool = palette.slice(0)
        for (var i = pool.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1))
            var tmp = pool[i]
            pool[i] = pool[j]
            pool[j] = tmp
        }

        var colors = ({})
        for (var s = 0; s < stems.length; s++)
            colors[stems[s].name] = pool[s % pool.length]
        stemColors = colors
    }

    function popupStatusText(msg) {
        if (!msg) return "Processing..."
        var match = msg.match(/Initializing Demucs \(([^)]+)\)/)
        if (match && match.length > 1) return match[1]
        return msg
    }

    function setActiveSection(index) {
        var next = Math.max(0, Math.min(3, index))
        if (next === activeSection)
            return
        contentArea.previousSection = activeSection
        contentArea.transitionDirection = next > activeSection ? 1 : -1
        activeSection = next
        contentArea.restartPageTransition()
    }

    function shiftSection(delta) {
        setActiveSection(activeSection + delta)
    }

    Rectangle {
        id: mainRect
        anchors.fill: parent
        radius: 12
        color: "#121414"

        // ===== RESIZE HANDLES (high z-order to stay above content) =====
        MouseArea { z: 100; width: parent.width; height: 6; anchors.top: parent.top; cursorShape: Qt.SizeVerCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.height -= (mouseY - clickPos.y); app.y += (mouseY - clickPos.y) } }
        }
        MouseArea { z: 100; width: parent.width; height: 6; anchors.bottom: parent.bottom; cursorShape: Qt.SizeVerCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.height += (mouseY - clickPos.y) } }
        }
        MouseArea { z: 100; width: 6; height: parent.height; anchors.left: parent.left; cursorShape: Qt.SizeHorCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width -= (mouseX - clickPos.x); app.x += (mouseX - clickPos.x) } }
        }
        MouseArea { z: 100; width: 6; height: parent.height; anchors.right: parent.right; cursorShape: Qt.SizeHorCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width += (mouseX - clickPos.x) } }
        }
        MouseArea { z: 100; width: 16; height: 16; anchors.top: parent.top; anchors.left: parent.left; cursorShape: Qt.SizeFDiagCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width -= (mouseX - clickPos.x); app.x += (mouseX - clickPos.x); app.height -= (mouseY - clickPos.y); app.y += (mouseY - clickPos.y) } }
        }
        MouseArea { z: 100; width: 16; height: 16; anchors.top: parent.top; anchors.right: parent.right; cursorShape: Qt.SizeBDiagCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width += (mouseX - clickPos.x); app.height -= (mouseY - clickPos.y); app.y += (mouseY - clickPos.y) } }
        }
        MouseArea { z: 100; width: 16; height: 16; anchors.bottom: parent.bottom; anchors.left: parent.left; cursorShape: Qt.SizeBDiagCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width -= (mouseX - clickPos.x); app.x += (mouseX - clickPos.x); app.height += (mouseY - clickPos.y) } }
        }
        MouseArea { z: 100; width: 16; height: 16; anchors.bottom: parent.bottom; anchors.right: parent.right; cursorShape: Qt.SizeFDiagCursor
            property point clickPos
            onPressed: { clickPos = Qt.point(mouseX, mouseY) }
            onPositionChanged: { if (pressed) { app.width += (mouseX - clickPos.x); app.height += (mouseY - clickPos.y) } }
        }

        Column {
            anchors.fill: parent
            spacing: 0

            TopBar {
                id: topBar
                gpuInfo: backend ? backend.gpuInfo : "Checking..."
                gpuAvailable: backend ? backend.gpuAvailable : false
                hasUpdate: backend ? backend.updateAvailable : false
                activeTab: activeSection
                onTabClicked: function(i) { setActiveSection(i) }
                onMinimizeClicked: app.showMinimized()
                onCloseClicked: Qt.quit()
            }

            Item {
                id: contentArea
                width: parent.width
                height: parent.height - topBar.height - 72
                clip: true
                property int transitionDirection: 1
                property int previousSection: -1
                property bool isPageTransitioning: false
                property real pageOffset: 0
                property real previousPageOffset: 0
                property real swipeOffset: 0
                property bool isSwiping: false
                property int swipeTargetSection: {
                    if (!isSwiping || Math.abs(swipeOffset) < 10)
                        return -1
                    return Math.max(0, Math.min(3, activeSection + (swipeOffset < 0 ? 1 : -1)))
                }

                function restartPageTransition() {
                    isPageTransitioning = true
                    pageOffset = transitionDirection * contentArea.width
                    previousPageOffset = 0
                    pageOpacity = 0.86
                    pageTransition.restart()
                }

                function finishSwipe(next, offset) {
                    next = Math.max(0, Math.min(3, next))
                    if (next === activeSection) {
                        swipeOffset = 0
                        isSwiping = false
                        return
                    }

                    previousSection = activeSection
                    transitionDirection = next > activeSection ? 1 : -1
                    previousPageOffset = offset
                    pageOffset = (transitionDirection > 0 ? contentArea.width : -contentArea.width) + offset
                    pageOpacity = 1.0
                    isSwiping = false
                    swipeOffset = 0
                    isPageTransitioning = true
                    activeSection = next
                    pageTransition.restart()
                }

                function sectionVisible(index) {
                    return index === activeSection
                           || (isPageTransitioning && index === previousSection)
                           || (isSwiping && index === swipeTargetSection)
                }

                function sectionX(index) {
                    if (isPageTransitioning) {
                        if (index === activeSection)
                            return pageOffset
                        if (index === previousSection)
                            return previousPageOffset
                    }

                    if (isSwiping) {
                        if (index === activeSection)
                            return swipeOffset
                        if (index === swipeTargetSection)
                            return swipeOffset < 0
                                   ? contentArea.width + swipeOffset
                                   : -contentArea.width + swipeOffset
                    }

                    return 0
                }

                property real pageOpacity: 1.0

                SequentialAnimation {
                    id: pageTransition
                    ParallelAnimation {
                        NumberAnimation { target: contentArea; property: "pageOffset"; to: 0; duration: 170; easing.type: Easing.OutCubic }
                        NumberAnimation { target: contentArea; property: "previousPageOffset"; to: -contentArea.transitionDirection * contentArea.width; duration: 170; easing.type: Easing.OutCubic }
                        NumberAnimation { target: contentArea; property: "pageOpacity"; to: 1.0; duration: 130; easing.type: Easing.OutQuad }
                    }
                    onStopped: {
                        contentArea.isPageTransitioning = false
                        contentArea.previousSection = -1
                        contentArea.previousPageOffset = 0
                    }
                }

                WheelHandler {
                    target: contentArea
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    onWheel: function(event) {
                        var dx = event.angleDelta.x
                        var dy = event.angleDelta.y
                        if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.25) {
                            event.accepted = false
                            return
                        }
                        shiftSection(dx < 0 ? 1 : -1)
                        event.accepted = true
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    property real startX: 0
                    property bool isHorizontalSwipe: false

                    onPressed: function(mouse) {
                        startX = mouse.x
                        isHorizontalSwipe = false
                        contentArea.isSwiping = true
                    }

                    onPositionChanged: function(mouse) {
                        var dx = mouse.x - startX
                        if (Math.abs(dx) > 10) {
                            isHorizontalSwipe = true
                        }
                        if (isHorizontalSwipe) {
                            contentArea.swipeOffset = dx
                        }
                    }

                    onReleased: function(mouse) {
                        var dx = mouse.x - startX
                        if (Math.abs(dx) > 50) {
                            contentArea.finishSwipe(activeSection + (dx > 0 ? -1 : 1), dx)
                        } else {
                            contentArea.isSwiping = false
                            contentArea.swipeOffset = 0
                        }
                    }

                    onCanceled: {
                        contentArea.isSwiping = false
                        contentArea.swipeOffset = 0
                    }
                }

                // ===== DASHBOARD (Section 0) =====
                Rectangle {
                    width: parent.width
                    height: parent.height
                    y: 0
                    x: contentArea.sectionX(0)
                    opacity: activeSection === 0 ? contentArea.pageOpacity : 1.0
                    color: "transparent"
                    visible: contentArea.sectionVisible(0)
                    enabled: activeSection === 0

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: dashCol.height + 60
                        clip: true
                        interactive: !contentArea.isSwiping
                        ScrollBar.vertical: ScrollBar { width: 4; policy: ScrollBar.AsNeeded }

                        Column {
                            id: dashCol
                            width: parent.width
                            spacing: 24

                            Column { spacing: 6
                                Text { text: "Source Separation"; color: "#e2e2e2"; font.family: "Montserrat"; font.pixelSize: 30; font.weight: Font.Bold }
                                Text { text: "Upload an audio file to deconstruct into high-fidelity stems."; color: Qt.rgba(0.73, 0.8, 0.73, 0.55); font.family: "Inter"; font.pixelSize: 14 }
                            }

                            Rectangle {
                                width: parent.width
                                height: 280
                                radius: 32
                                color: "transparent"
                                border.color: Qt.rgba(1, 1, 1, 0.12)
                                border.width: 2


                                DropZone {
                                    anchors.fill: parent
                                    onFileDropped: function(path) {
                                        if (backend) {
                                            loadingPopup.statusText = "Preparing audio file..."
                                            loadingOverlay.visible = true
                                            loadingDelayTimer.callback = function() {
                                                setActiveSection(1)
                                                backend.startSplit(path)
                                            }
                                            loadingDelayTimer.start()
                                        }
                                    }
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 24

                                Rectangle {
                                    width: (parent.width - 24) * 0.62
                                    height: 200
                                    radius: 24
                                    color: Qt.rgba(1, 1, 1, 0.03)
                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                    border.width: 1

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 20
                                        spacing: 12

                                        Row { spacing: 8
                                            Text { text: "\uE889"; font.family: "Material Symbols Outlined"; color: "#e2e2e2"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Recent Separations"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                                        }

                                        ListView {
                                            id: historyList
                                            width: parent.width
                                            height: parent.height - 55
                                            interactive: false
                                            model: backend ? backend.historyModel : null
                                            delegate: Item {
                                                id: histDelegate
                                                width: parent.width; height: 44
                                                
                                                Rectangle {
                                                    anchors.fill: parent
                                                    radius: 8
                                                    color: histMouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
                                                    Behavior on color { ColorAnimation { duration: 150 } }
                                                }

                                                MouseArea {
                                                    id: histMouseArea
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    hoverEnabled: true
                                                    onClicked: {
                                                        if ((model.status === "ok" || model.status === "cached") && backend) {
                                                            loadingPopup.statusText = "Loading past separation..."
                                                            loadingOverlay.visible = true
                                                            loadingDelayTimer.callback = function() {
                                                                stemWaveforms = ({})
                                                                wavePanel.waveformData = []
                                                                wavePanel.hasAudio = false
                                                                backend.loadHistoryItem(model.file_path, model.stems)
                                                            }
                                                            loadingDelayTimer.start()
                                                        }
                                                    }
                                                }

                                                Rectangle { id: histIcon; x: 4; y: 4; width: 36; height: 36; radius: 8; color: Qt.rgba(0,0.89,0.53,0.08)
                                                    Text { anchors.centerIn: parent; text: "\uE40B"; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 16 }
                                                }
                                                Row { id: histActions; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; anchors.rightMargin: 4; spacing: 8
                                                    Text { text: "\uE037"; font.family: "Material Symbols Outlined"; color: histMouseArea.containsMouse ? "#00e388" : Qt.rgba(0.73,0.8,0.73,0.4); font.pixelSize: 14; Behavior on color { ColorAnimation { duration: 150 } } }
                                                    Text { text: "\uE2C4"; font.family: "Material Symbols Outlined"; color: histMouseArea.containsMouse ? "#00e388" : Qt.rgba(0.73,0.8,0.73,0.4); font.pixelSize: 14; Behavior on color { ColorAnimation { duration: 150 } } }
                                                }
                                                Column { anchors.verticalCenter: parent.verticalCenter; anchors.left: histIcon.right; anchors.leftMargin: 12; anchors.right: histActions.left; anchors.rightMargin: 8
                                                    Text { text: model.file_name || ""; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 14; font.weight: Font.Medium; elide: Text.ElideMiddle; width: parent.width }
                                                    Row { spacing: 4
                                                        Text { text: (model.status === "ok" || model.status === "cached") ? (model.stems && model.stems.indexOf("[") === 0 ? (JSON.parse(model.stems).length + " Stems") : "Stems") : ""; color: Qt.rgba(0.73,0.8,0.73,0.4); font.family: "Inter"; font.pixelSize: 11 }
                                                        Text { text: ((model.status === "ok" || model.status === "cached") && model.created_at) ? "\u2022" : ""; color: Qt.rgba(0.73,0.8,0.73,0.3); font.family: "Inter"; font.pixelSize: 11 }
                                                        Text { text: model.created_at || ""; color: Qt.rgba(0.73,0.8,0.73,0.4); font.family: "Inter"; font.pixelSize: 11 }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    width: (parent.width - 24) * 0.38
                                    height: 200
                                    radius: 24
                                    color: Qt.rgba(1, 1, 1, 0.03)
                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                    border.width: 1

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 20
                                        spacing: 12

                                        Text { text: "Engine Status"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold }

                                        Column { width: parent.width; spacing: 4
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "GPU LOAD"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? backend.gpuLoad : 0) + "%"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend ? backend.gpuLoad : 0) / 100, 1); height: parent.height; radius: 2; color: "#00e388" }
                                            }
                                        }

                                        Column { width: parent.width; spacing: 4
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "VRAM"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? backend.vramUsed : "0") + " / " + (backend ? backend.vramTotal : "0") + " MB"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend && backend.vramTotal !== "0" ? parseFloat(backend.vramUsed) / parseFloat(backend.vramTotal) : 0), 1); height: parent.height; radius: 2; color: Qt.rgba(0.73,0.8,0.73,0.4) }
                                            }
                                        }

                                        Text { text: backend ? backend.gpuInfo : "Checking..."; color: "#00e388"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Medium }
                                    }
                                }
                            }
                        }
                    }
                }

                // ===== PROCESSING (Section 1) =====
                Rectangle {
                    width: parent.width
                    height: parent.height
                    y: 0
                    x: contentArea.sectionX(1)
                    opacity: activeSection === 1 ? contentArea.pageOpacity : 1.0
                    color: "transparent"
                    visible: contentArea.sectionVisible(1)
                    enabled: activeSection === 1

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: procCol.height + 60
                        clip: true
                        interactive: !contentArea.isSwiping
                        ScrollBar.vertical: ScrollBar { width: 4; policy: ScrollBar.AsNeeded }

                        Column {
                            id: procCol
                            width: parent.width
                            spacing: 24

                            Column { spacing: 8; width: parent.width
                                Item { width: parent.width; height: 34
                                    Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "Processing Audio"; color: "#e2e2e2"; font.family: "Montserrat"; font.pixelSize: 28; font.weight: Font.Bold }
                                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: app.procProgress + "%"; color: "#00e388"; font.family: "Montserrat"; font.pixelSize: 22; font.weight: Font.Bold }
                                }
                                Text { text: "Splitting audio into separate stems..."; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 14 }

                                Rectangle { width: parent.width; height: 6; radius: 3; color: Qt.rgba(1,1,1,0.06)
                                    Rectangle { height: parent.height; radius: 3; color: "#00e388"; width: parent.width * app.procProgress / 100; Behavior on width { NumberAnimation { duration: 400 } } }
                                }
                            }

                            WavePanel {
                                id: wavePanel
                                width: parent.width
                                height: 200
                                panelLabel: "Original Waveform"
                                playPosition: audioEngine && audioEngine.duration > 0
                                              ? Math.max(0, Math.min(1, audioEngine.position / audioEngine.duration))
                                              : 0
                            }

                            Row {
                                width: parent.width
                                spacing: 24

                                Rectangle {
                                    width: (parent.width - 24) * 0.62
                                    height: 200
                                    radius: 24
                                    color: Qt.rgba(1, 1, 1, 0.03)
                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                    border.width: 1

                                    Item {
                                        anchors.fill: parent; anchors.margins: 20
                                        Text {
                                            id: logHeader
                                            anchors.top: parent.top; anchors.left: parent.left
                                            text: "\uEB8E  Status Log"
                                            color: "#e2e2e2"
                                            font.family: "Inter"
                                            font.pixelSize: 16
                                            font.weight: Font.DemiBold
                                        }
                                        Rectangle {
                                            anchors { top: logHeader.bottom; bottom: parent.bottom; left: parent.left; right: parent.right; topMargin: 8 }
                                            radius: 8; color: Qt.rgba(0,0,0,0.25)
                                            Column { anchors.fill: parent; anchors.margins: 12
                                                Text { text: statusLabel.text || "Waiting for file..."; color: statusLabel.text && statusLabel.text.indexOf("not found") > 0 ? "#ffb4ab" : "#00e388"; font.family: "Inter"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    width: (parent.width - 24) * 0.38
                                    height: 200
                                    radius: 24
                                    color: Qt.rgba(1, 1, 1, 0.03)
                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                    border.width: 1

                                    Column {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 8
                                        Text { text: "Resource Usage"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 16; font.weight: Font.DemiBold }

                                        Column { width: parent.width; spacing: 4
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "GPU LOAD"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? backend.gpuLoad : 0) + "%"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend ? backend.gpuLoad : 0) / 100, 1); height: parent.height; radius: 2; color: "#00e388" }
                                            }
                                        }

                                        Column { width: parent.width; spacing: 4
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "VRAM"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? backend.vramUsed : "0") + " / " + (backend ? backend.vramTotal : "0") + " MB"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend && backend.vramTotal !== "0" ? parseFloat(backend.vramUsed) / parseFloat(backend.vramTotal) : 0), 1); height: parent.height; radius: 2; color: Qt.rgba(0.73,0.8,0.73,0.4) }
                                            }
                                        }

                                        Text { text: backend ? backend.gpuInfo : "Checking..."; color: "#00e388"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Medium; elide: Text.ElideRight }

                                    }
                                }
                            }
                        }
                    }
                }

                // ===== STEM MIXER (Section 2) =====
                Rectangle {
                    width: parent.width
                    height: parent.height
                    y: 0
                    x: contentArea.sectionX(2)
                    opacity: activeSection === 2 ? contentArea.pageOpacity : 1.0
                    color: "transparent"
                    visible: contentArea.sectionVisible(2)
                    enabled: activeSection === 2

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: mixCol.height + 60
                        clip: true
                        interactive: !contentArea.isSwiping
                        ScrollBar.vertical: ScrollBar { width: 4; policy: ScrollBar.AsNeeded }

                        Column {
                            id: mixCol
                            width: parent.width
                            spacing: 24

                            Item { width: parent.width; height: 70
                                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                    Text { text: "Stem Mixer"; color: "#e2e2e2"; font.family: "Montserrat"; font.pixelSize: 30; font.weight: Font.Bold }
                                    Text { text: "Fine-tune individual components of your track with AI precision."; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 14 }
                                }
                            }

                            Repeater {
                                id: stemRepeater
                                model: currentStems
                                delegate: StemTrack {
                                    width: parent.width
                                    stemId: modelData.name
                                    stemName: modelData.name
                                    stemLabel: "STEM " + ("0" + (index + 1)).slice(-2)
                                    accentColor: stemColors[modelData.name] || "#00e388"
                                    waveformData: stemWaveforms[modelData.name] || []
                                    isSolo: soloStem === modelData.name
                                    isMuted: manualMutes[modelData.name] === true || (soloStem !== "" && soloStem !== modelData.name)
                                    onMuteClicked: {
                                        if (soloStem !== "") return
                                        var m = ({})
                                        for (var k in manualMutes) m[k] = manualMutes[k]
                                        m[modelData.name] = !m[modelData.name]
                                        manualMutes = m
                                        if (audioEngine) audioEngine.toggleMute(modelData.name)
                                    }
                                    onSoloClicked: {
                                        if (soloStem === modelData.name) {
                                            soloStem = ""
                                            if (audioEngine) audioEngine.clearSolo()
                                        } else {
                                            soloStem = modelData.name
                                            if (audioEngine) audioEngine.setSolo(modelData.name)
                                        }
                                    }
                                    onGainAdjusted: function(v) { if (audioEngine) audioEngine.setStemGain(modelData.name, v) }
                                    onDownloadClicked: { if (audioEngine) audioEngine.exportStem(modelData.name) }
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 24
                                visible: currentStems.length > 0

                                Repeater {
                                    model: [
                                        {icon: "\uE9E4", label: "Sample Rate", value: "48 kHz / 24-bit"},
                                        {icon: "\uEF5B", label: "Processing Load", value: "0.0% CPU"},
                                        {icon: "\uE889", label: "Last Edit", value: "Just now"}
                                    ]
                                    delegate: Rectangle {
                                        width: (parent.width - 48) / 3
                                        height: 80
                                        radius: 16
                                        color: Qt.rgba(1,1,1,0.03)
                                        border.color: Qt.rgba(1,1,1,0.08)
                                        border.width: 1

                                        Row { anchors.fill: parent; anchors.margins: 16; spacing: 12
                                            Rectangle { width: 40; height: 40; radius: 8; color: Qt.rgba(0,0.89,0.53,0.08); anchors.verticalCenter: parent.verticalCenter
                                                Text { anchors.centerIn: parent; text: modelData.icon; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 20 }
                                            }
                                            Column { anchors.verticalCenter: parent.verticalCenter
                                                Text { text: modelData.label; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { text: modelData.value; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.Bold }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ===== SETTINGS (Section 3) =====
                Rectangle {
                    width: parent.width
                    height: parent.height
                    y: 0
                    x: contentArea.sectionX(3)
                    opacity: activeSection === 3 ? contentArea.pageOpacity : 1.0
                    color: "transparent"
                    visible: contentArea.sectionVisible(3)
                    enabled: activeSection === 3

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: setCol.height + 60
                        clip: true
                        interactive: !contentArea.isSwiping
                        ScrollBar.vertical: ScrollBar { width: 4; policy: ScrollBar.AsNeeded }

                        Column {
                            id: setCol
                            width: parent.width
                            spacing: 24

                            Column { spacing: 6
                                Text { text: "System Preferences"; color: "#e2e2e2"; font.family: "Montserrat"; font.pixelSize: 30; font.weight: Font.Bold }
                                Text { text: "Configure AI hardware acceleration and export parameters."; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 14 }
                            }

                            Row { width: parent.width; spacing: 24
                                Rectangle { width: (parent.width - 24) * 0.48; height: 330; radius: 24; color: Qt.rgba(1,1,1,0.03); border.color: Qt.rgba(1,1,1,0.08); border.width: 1
                                    Column { anchors.fill: parent; anchors.margins: 20; spacing: 16
                                        Item { width: parent.width; height: 24
                                            Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "Acceleration Engine"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                            Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "\uE322"; font.family: "Material Symbols Outlined"; color: "#e2e2e2"; font.pixelSize: 20 }
                                        }
                                        Rectangle { width: parent.width; height: 52; radius: 10; color: backend && backend.gpuAvailable ? Qt.rgba(0,0.89,0.53,0.04) : "transparent"; border.color: backend && backend.gpuAvailable ? Qt.rgba(0,0.89,0.53,0.25) : Qt.rgba(1,1,1,0.06); border.width: 1
                                            Item { anchors.fill: parent; anchors.margins: 16
                                                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                                    Text { text: "NVIDIA CUDA (GPU)"; color: backend && backend.gpuAvailable ? "#00e388" : Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                                    Text { text: "Recommended for batch processing"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11 }
                                                }
                                                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 18; height: 18; radius: 9; color: "#00e388"; visible: backend && backend.gpuAvailable
                                                    Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: "#121414" }
                                                }
                                            }
                                        }
                                        Rectangle { width: parent.width; height: 52; radius: 10; color: backend && backend.gpuAvailable ? "transparent" : Qt.rgba(1,0.78,0.34,0.06); border.color: backend && backend.gpuAvailable ? Qt.rgba(1,1,1,0.06) : Qt.rgba(1,0.78,0.34,0.35); border.width: 1
                                            Item { anchors.fill: parent; anchors.margins: 16
                                                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                                    Text { text: "CPU Cluster"; color: backend && backend.gpuAvailable ? Qt.rgba(0.73,0.8,0.73,0.45) : "#FFC857"; font.family: "Inter"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                                    Text { text: "Standard high-precision threads"; color: Qt.rgba(0.73,0.8,0.73,0.35); font.family: "Inter"; font.pixelSize: 11 }
                                                }
                                                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 18; height: 18; radius: 9; color: "#FFC857"; visible: !(backend && backend.gpuAvailable)
                                                    Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: "#121414" }
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle { width: (parent.width - 24) * 0.48; height: 330; radius: 24; color: Qt.rgba(1,1,1,0.03); border.color: Qt.rgba(1,1,1,0.08); border.width: 1
                                    Column { anchors.fill: parent; anchors.margins: 20; spacing: 18
                                        Item { width: parent.width; height: 24
                                            Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "Demucs Configuration"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                            Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "\uE322"; font.family: "Material Symbols Outlined"; color: "#e2e2e2"; font.pixelSize: 20 }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Text { text: "Model"; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 12 }
                                            ModernCombo {
                                                id: modelBox
                                                width: parent.width
                                                model: ["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_extra"]
                                                currentIndex: 2
                                                onCurrentTextChanged: {
                                                    selectedModel = currentText
                                                    backend.selectedModel = currentText
                                                }
                                            }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Text { text: "Segment Size: " + segmentSlider.value; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 12 }
                                            ModernSlider {
                                                id: segmentSlider
                                                width: parent.width
                                                from: 1
                                                to: 30
                                                stepSize: 1
                                                value: 5
                                                onValueChanged: {
                                                    segmentSize = value
                                                    backend.segmentSize = value
                                                }
                                            }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Text { text: "Overlap: " + overlapSlider.value.toFixed(2); color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 12 }
                                            ModernSlider {
                                                id: overlapSlider
                                                width: parent.width
                                                from: 0.1
                                                to: 0.9
                                                stepSize: 0.05
                                                value: 0.25
                                                onValueChanged: {
                                                    overlapValue = value
                                                    backend.overlap = value
                                                }
                                            }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Text { text: "Shifts: " + shiftsSlider.value + " (quality multiplier)"; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 12 }
                                            ModernSlider {
                                                id: shiftsSlider
                                                width: parent.width
                                                from: 1
                                                to: 4
                                                stepSize: 1
                                                value: 1
                                                onValueChanged: {
                                                    shiftsValue = value
                                                    backend.shifts = value
                                                }
                                            }
                                        }
                                    }
                                }

                            }
                            Row { width: parent.width; spacing: 24
                                Rectangle { width: (parent.width - 24) * 0.48; height: 200; radius: 24; color: Qt.rgba(1,1,1,0.03); border.color: Qt.rgba(1,1,1,0.08); border.width: 1
                                    Column { anchors.fill: parent; anchors.margins: 20; spacing: 16
                                        Text { text: "Real-time Telemetry"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                        Column { width: parent.width; spacing: 6
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "GPU VRAM Usage"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? (parseFloat(backend.vramUsed) / 1024).toFixed(1) : "0") + " / " + (backend ? (parseFloat(backend.vramTotal) / 1024).toFixed(1) : "0") + " GB"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend && backend.vramTotal !== "0" ? parseFloat(backend.vramUsed) / parseFloat(backend.vramTotal) : 0), 1); height: parent.height; radius: 2; color: "#00e388" }
                                            }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Item { width: parent.width; height: 14
                                                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "GPU Load"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 0.8 }
                                                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: (backend ? backend.gpuLoad : "0") + "%"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.weight: Font.Medium }
                                            }
                                            Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                Rectangle { width: parent.width * Math.min((backend ? backend.gpuLoad : 0) / 100, 1); height: parent.height; radius: 2; color: "#00e388" }
                                            }
                                        }
                                    }
                                }

                                // ===== SOFTWARE UPDATES CARD =====
                                Rectangle {
                                    width: (parent.width - 24) * 0.52; height: 200; radius: 24
                                    color: Qt.rgba(1,1,1,0.03)
                                    border.color: updateStatus === "available" ? Qt.rgba(0, 0.89, 0.53, 0.25) : Qt.rgba(1,1,1,0.08)
                                    border.width: 1
                                    Behavior on border.color { ColorAnimation { duration: 300 } }

                                    Column {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 14

                                        // Header row
                                        Item { width: parent.width; height: 24
                                            Row { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                                Text { text: "\uE923"; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 20; anchors.verticalCenter: parent.verticalCenter }
                                                Text { text: "Software Updates"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                                            }
                                            Text {
                                                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                                text: "v" + (backend ? backend.appVersion : "---")
                                                color: Qt.rgba(0.73, 0.8, 0.73, 0.55)
                                                font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Medium
                                            }
                                        }

                                        // Status display
                                        Rectangle {
                                            width: parent.width; height: 52; radius: 10
                                            color: {
                                                if (updateStatus === "available") return Qt.rgba(0, 0.89, 0.53, 0.04)
                                                if (updateStatus === "ready") return Qt.rgba(0, 0.89, 0.53, 0.06)
                                                if (updateStatus === "error") return Qt.rgba(1, 0.3, 0.43, 0.04)
                                                return Qt.rgba(1, 1, 1, 0.02)
                                            }
                                            border.color: {
                                                if (updateStatus === "available" || updateStatus === "ready") return Qt.rgba(0, 0.89, 0.53, 0.25)
                                                if (updateStatus === "error") return Qt.rgba(1, 0.3, 0.43, 0.25)
                                                return Qt.rgba(1, 1, 1, 0.06)
                                            }
                                            border.width: 1

                                            Item { anchors.fill: parent; anchors.margins: 12
                                                // Checking spinner
                                                Row {
                                                    anchors.verticalCenter: parent.verticalCenter; spacing: 10
                                                    visible: updateStatus === "checking"
                                                    Canvas {
                                                        id: updateSpinner; width: 18; height: 18
                                                        onPaint: {
                                                            var ctx = getContext("2d"); ctx.clearRect(0,0,width,height);
                                                            ctx.strokeStyle = "#00e388"; ctx.lineWidth = 2.5; ctx.lineCap = "round";
                                                            ctx.beginPath(); ctx.arc(9, 9, 6.5, 0, 1.4 * Math.PI); ctx.stroke();
                                                        }
                                                        RotationAnimator { target: updateSpinner; from: 0; to: 360; duration: 900; running: updateStatus === "checking"; loops: Animation.Infinite }
                                                    }
                                                    Text { text: "Checking for updates..."; color: Qt.rgba(0.73,0.8,0.73,0.6); font.family: "Inter"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                                }

                                                // Up to date
                                                Row {
                                                    anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                                    visible: updateStatus === "uptodate"
                                                    Text { text: "\uE86C"; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                                    Text { text: "You're up to date"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
                                                }

                                                // Update available
                                                Item {
                                                    anchors.fill: parent
                                                    visible: updateStatus === "available"
                                                    Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                                        Text { text: "v" + updateVersion + " available"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                                        Text { text: updateNotes; color: Qt.rgba(0.73,0.8,0.73,0.5); font.family: "Inter"; font.pixelSize: 11; elide: Text.ElideRight; width: 220 }
                                                    }
                                                }

                                                // Downloading
                                                Column {
                                                    anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                                    visible: updateStatus === "downloading"
                                                    Item { width: parent.width; height: 16
                                                        Text { anchors.left: parent.left; text: "Downloading update..."; color: Qt.rgba(0.73,0.8,0.73,0.6); font.family: "Inter"; font.pixelSize: 12 }
                                                        Text { anchors.right: parent.right; text: updateProgress + "%"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Medium }
                                                    }
                                                    Rectangle { width: parent.width; height: 4; radius: 2; color: Qt.rgba(1,1,1,0.06)
                                                        Rectangle { width: parent.width * updateProgress / 100; height: parent.height; radius: 2; color: "#00e388"; Behavior on width { NumberAnimation { duration: 200 } } }
                                                    }
                                                }

                                                // Ready to install
                                                Row {
                                                    anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                                    visible: updateStatus === "ready"
                                                    Text { text: "\uE86C"; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                                    Text { text: "Download complete — ready to install"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
                                                }

                                                // Error
                                                Row {
                                                    anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                                    visible: updateStatus === "error"
                                                    Text { text: "\uE000"; font.family: "Material Symbols Outlined"; color: "#ffb4ab"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                                    Text { text: "Could not check for updates"; color: "#ffb4ab"; font.family: "Inter"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                                }

                                                // Idle (no status yet)
                                                Row {
                                                    anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                                    visible: updateStatus === ""
                                                    Text { text: "\uE8B8"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.4); font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                                    Text { text: "Click below to check for updates"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                                }
                                            }
                                        }

                                        // Action buttons row
                                        Row { spacing: 10
                                            // Check / Retry button
                                            Rectangle {
                                                width: 160; height: 34; radius: 8
                                                visible: updateStatus !== "downloading" && updateStatus !== "ready"
                                                color: updateCheckMa.containsMouse ? Qt.rgba(0, 0.89, 0.53, 0.16) : Qt.rgba(0, 0.89, 0.53, 0.08)
                                                border.color: Qt.rgba(0, 0.89, 0.53, 0.35); border.width: 1
                                                Behavior on color { ColorAnimation { duration: 150 } }

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: updateStatus === "checking" ? "Checking..." : "Check for Updates"
                                                    color: "#00e388"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.DemiBold
                                                }
                                                MouseArea {
                                                    id: updateCheckMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                    enabled: updateStatus !== "checking"
                                                    onClicked: { if (backend) backend.checkForUpdates() }
                                                }
                                            }

                                            // Download button
                                            Rectangle {
                                                width: 160; height: 34; radius: 8
                                                visible: updateStatus === "available"
                                                color: updateDlMa.containsMouse ? "#14f19b" : "#00e388"
                                                Behavior on color { ColorAnimation { duration: 150 } }

                                                Text { anchors.centerIn: parent; text: "Download Update"; color: "#00391e"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Bold }
                                                MouseArea {
                                                    id: updateDlMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                    onClicked: { if (backend) backend.downloadUpdate() }
                                                }
                                            }

                                            // Install & Restart button
                                            Rectangle {
                                                width: 190; height: 34; radius: 8
                                                visible: updateStatus === "ready"
                                                color: updateInstMa.containsMouse ? "#14f19b" : "#00e388"
                                                Behavior on color { ColorAnimation { duration: 150 } }

                                                Row { anchors.centerIn: parent; spacing: 6
                                                    Text { text: "\uE923"; font.family: "Material Symbols Outlined"; color: "#00391e"; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                                                    Text { text: "Install & Restart"; color: "#00391e"; font.family: "Inter"; font.pixelSize: 12; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                                }
                                                MouseArea {
                                                    id: updateInstMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                    onClicked: { if (backend) backend.installUpdate() }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ===== BOTTOM PLAYER BAR =====
            Rectangle {
                id: bottomBar
                width: parent.width
                height: 72
                color: Qt.rgba(0.12, 0.12, 0.12, 0.85)

                // --- Full-width progress bar at the very top (YouTube Music style) ---
                Item {
                    id: progressBarArea
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 16
                    z: 10

                    property bool hovered: progressBarMouseArea.containsMouse || progressBarMouseArea.pressed

                    // Track background
                    Rectangle {
                        id: progressTrack
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: progressBarArea.hovered ? 5 : 3
                        color: Qt.rgba(1, 1, 1, 0.12)

                        Behavior on height {
                            NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
                        }

                        // Progress fill
                        Rectangle {
                            id: progressFill
                            width: audioEngine && audioEngine.duration > 0
                                   ? parent.width * (audioEngine.position / audioEngine.duration)
                                   : 0
                            height: parent.height
                            color: "#00e388"

                            Behavior on width {
                                NumberAnimation {
                                    duration: 120
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }

                        // Thumb circle
                        Rectangle {
                            id: progressThumb
                            width: 12
                            height: 12
                            radius: 6
                            color: "#00e388"
                            visible: progressBarArea.hovered
                            y: (parent.height - height) / 2
                            x: progressFill.width - width / 2
                        }
                    }

                    MouseArea {
                        id: progressBarMouseArea
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: parent.height
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: function(mouse) {
                            if (audioEngine) {
                                var ratio = mouse.x / width
                                audioEngine.seek(ratio * audioEngine.duration)
                            }
                        }
                        onPositionChanged: function(mouse) {
                            if (pressed && audioEngine) {
                                var ratio = Math.max(0, Math.min(1, mouse.x / width))
                                audioEngine.seek(ratio * audioEngine.duration)
                            }
                        }
                    }

                    // Time labels positioned below the progress track
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.top: progressTrack.bottom
                        anchors.topMargin: 1
                        text: audioEngine ? Qt.formatTime(new Date(audioEngine.position * 1000), "mm:ss") : "00:00"
                        color: progressBarArea.hovered ? "#00e388" : Qt.rgba(0.73, 0.8, 0.73, 0.45)
                        font.family: "Inter"
                        font.pixelSize: 10
                        font.weight: Font.Medium
                        visible: progressBarArea.hovered

                        Behavior on color {
                            ColorAnimation { duration: 150 }
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.top: progressTrack.bottom
                        anchors.topMargin: 1
                        text: audioEngine ? Qt.formatTime(new Date(audioEngine.duration * 1000), "mm:ss") : "00:00"
                        color: progressBarArea.hovered ? Qt.rgba(0.73, 0.8, 0.73, 0.55) : Qt.rgba(0.73, 0.8, 0.73, 0.35)
                        font.family: "Inter"
                        font.pixelSize: 10
                        font.weight: Font.Medium
                        visible: progressBarArea.hovered

                        Behavior on color {
                            ColorAnimation { duration: 150 }
                        }
                    }
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 32
                    anchors.rightMargin: 32

                    Item {
                        width: parent.width * 0.3
                        height: parent.height
                        Row { anchors.verticalCenter: parent.verticalCenter; spacing: 10
                            Text { text: activeStemLabel(); color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 1; font.weight: Font.Medium; visible: currentStems.length > 0 }
                        }
                    }

                    Item {
                        width: parent.width * 0.4
                        height: parent.height

                        Column {
                            anchors.centerIn: parent
                            spacing: 10

                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 20

                                Text {
                                    text: "\uE043"
                                    font.family: "Material Symbols Outlined"
                                    color: Qt.rgba(0.73,0.8,0.73,0.45)
                                    font.pixelSize: 20
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "\uE045"
                                    font.family: "Material Symbols Outlined"
                                    color: Qt.rgba(0.73,0.8,0.73,0.45)
                                    font.pixelSize: 26
                                    anchors.verticalCenter: parent.verticalCenter
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (audioEngine) audioEngine.previous() }
                                    }
                                }

                                Rectangle {
                                    id: playBtn
                                    width: 48
                                    height: 48
                                    radius: 24
                                    property bool playing: false
                                    color: playing ? "#FF4D6D" : playBtn.containsMouse ? "#14f19b" : "#00e388"
                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    Text {
                                        anchors.centerIn: parent
                                        text: playBtn.playing ? "\uE034" : "\uE037"
                                        font.family: "Material Symbols Outlined"
                                        color: "#00391e"
                                        font.pixelSize: 28
                                    }

                                    Connections {
                                        target: audioEngine
                                        function onAllPlayingChanged() {
                                            playBtn.playing = audioEngine.allPlaying
                                        }
                                    }

                                    MouseArea {
                                        id: playBtnMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (audioEngine) audioEngine.togglePlayAll() }
                                    }
                                }

                                Text {
                                    text: "\uE044"
                                    font.family: "Material Symbols Outlined"
                                    color: Qt.rgba(0.73,0.8,0.73,0.45)
                                    font.pixelSize: 26
                                    anchors.verticalCenter: parent.verticalCenter
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (audioEngine) audioEngine.next() }
                                    }
                                }

                                Text {
                                    text: "\uE040"
                                    font.family: "Material Symbols Outlined"
                                    color: Qt.rgba(0.73,0.8,0.73,0.45)
                                    font.pixelSize: 20
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }


                        }
                    }

                    Item {
                        width: parent.width * 0.3
                        height: parent.height
                        Row { anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; spacing: 16
                            Text { text: "\uE030"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.pixelSize: 20; anchors.verticalCenter: parent.verticalCenter }
                            NeoSlider {
                                id: volumeSlider
                                width: 110
                                height: 24
                                from: 0
                                to: 100
                                value: 80
                                accent: "#8BE9C1"
                                onValueChanged: {
                                    if (audioEngine) audioEngine.setMasterVolume(value / 100.0)
                                }
                            }
                            Text { text: "\uE8B8"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.pixelSize: 20; anchors.verticalCenter: parent.verticalCenter; MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: setActiveSection(3) } }
                        }
                    }
                }
            }
        }
    }

    // Backend connections
    Text {
        id: statusLabel
        visible: false
    }

    Connections {
        target: backend
        function onSplitStarted(fp) {
            loadingPopup.statusText = "Preparing separation..."
            loadingOverlay.visible = true
            currentStems = []; stemColors = ({}); stemWaveforms = ({}); setActiveSection(1); if (audioEngine) audioEngine.clearAll()
            wavePanel.waveformData = []
            wavePanel.hasAudio = false
        }
        function onProgressUpdated(v) { app.procProgress = Math.min(v, 99) }
        function onStatusUpdated(msg) {
            statusLabel.text = msg
            if (loadingOverlay.visible) loadingPopup.statusText = popupStatusText(msg)
        }
        function onWaveformReady(name, data) {
            if (name !== "original") return
            wavePanel.waveformData = data || []
            wavePanel.hasAudio = data && data.length > 0
        }
        function onStemWaveformReady(name, data) {
            var wf = ({})
            for (var k in stemWaveforms) wf[k] = stemWaveforms[k]
            wf[name] = data
            stemWaveforms = wf
        }
        function onSplitFinished(status, stemsJson) {
            loadingOverlay.visible = false
            var stems = JSON.parse(stemsJson)
            if (status === "ok") {
                assignStemColors(stems)
                currentStems = stems; setActiveSection(2)
                if (audioEngine) audioEngine.loadStems(stems)
            } else {
                statusLabel.text = status
                app.procProgress = 0
            }
        }
    }

    Timer {
        id: demucsCheck
        interval: 500
        onTriggered: {
            if (backend)
                backend.startDemucsCheck()
        }
    }

    Timer {
        id: loadingDelayTimer
        interval: 50
        repeat: false
        property var callback: null
        onTriggered: {
            if (callback) callback()
        }
    }

    // ===== LOADING OVERLAY (inside mainRect so it's fully opaque) =====
    Rectangle {
        id: loadingOverlay
        parent: mainRect
        anchors.fill: parent
        z: 200
        visible: false
        color: Qt.rgba(0, 0, 0, 0.55)
        radius: mainRect.radius

        property alias statusText: loadingPopup.statusText

        Behavior on opacity { NumberAnimation { duration: 200 } }

        MouseArea { anchors.fill: parent; onClicked: {} }

        Rectangle {
            id: loadingPopup
            anchors.centerIn: parent
            width: 340
            height: activeSection === 1 ? 150 : 110
            radius: 20
            color: "#1a1c1e"
            border.color: Qt.rgba(0, 0.89, 0.53, 0.25)
            border.width: 1

            property string statusText: "Loading..."

            scale: loadingOverlay.visible ? 1.0 : 0.9
            Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                color: "transparent"
                radius: 19
                border.color: Qt.rgba(255, 255, 255, 0.05)
                border.width: 1
            }

            Row {
                anchors.centerIn: parent
                spacing: 24

                Item {
                    width: 44
                    height: 44
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: "transparent"
                        border.color: Qt.rgba(0, 0.89, 0.53, 0.1)
                        border.width: 4
                    }

                    Canvas {
                        id: spinnerCanvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            ctx.strokeStyle = "#00e388";
                            ctx.lineWidth = 4;
                            ctx.lineCap = "round";
                            ctx.beginPath();
                            ctx.arc(width/2, height/2, width/2 - ctx.lineWidth/2, 0, 1.5 * Math.PI);
                            ctx.stroke();
                        }

                        RotationAnimator {
                            target: spinnerCanvas
                            from: 0
                            to: 360
                            duration: 1000
                            running: loadingOverlay.visible
                            loops: Animation.Infinite
                        }
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Text {
                        text: loadingPopup.statusText
                        width: 210
                        elide: Text.ElideRight
                        color: "#e2e2e2"
                        font.family: "Inter"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text: "Please wait..."
                        color: Qt.rgba(0.73, 0.8, 0.73, 0.5)
                        font.family: "Inter"
                        font.pixelSize: 12
                    }

                    Rectangle {
                        width: 86
                        height: 30
                        radius: 8
                        visible: activeSection === 1
                        color: cancelPopupMouse.containsMouse ? Qt.rgba(1, 0.3, 0.43, 0.16) : Qt.rgba(1, 0.3, 0.43, 0.08)
                        border.color: Qt.rgba(1, 0.3, 0.43, 0.35)
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "Cancel"
                            color: "#ffb4ab"
                            font.family: "Inter"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        MouseArea {
                            id: cancelPopupMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                loadingPopup.statusText = "Cancelling..."
                                if (backend) backend.cancelSplit()
                            }
                        }
                    }
                }
            }
        }
    }

    // --- Update backend connections ---
    Connections {
        target: backend
        function onUpdateStatusChanged(status) {
            updateStatus = status
        }
        function onUpdateAvailableChanged() {
            updateVersion = backend.updateVersion
            updateNotes = backend.updateNotes
        }
        function onUpdateDownloadProgressChanged() {
            updateProgress = backend.updateDownloadProgress
        }
    }

    Timer {
        id: updateCheckTimer
        interval: 3000
        repeat: false
        onTriggered: {
            if (backend) backend.checkForUpdates()
        }
    }

    Component.onCompleted: {
        if (backend) {
            backend.checkGpu()
            demucsCheck.start()
            updateCheckTimer.start()
        }
    }
}
