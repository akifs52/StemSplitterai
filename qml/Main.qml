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

    title: "SonicSplit AI"

    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"

    property var currentStems: []
    property int activeSection: 0
    property int procProgress: 0
    property string selectedModel: "htdemucs"
    property int segmentSize: 10
    property real overlapValue: 0.25
    property int shiftsValue: 1
    property string soloStem: ""
    property var manualMutes: ({})

    function formatTime(sec) {
        sec = Math.floor(sec)
        var m = Math.floor(sec / 60)
        var s = sec % 60
        return m + ":" + (s < 10 ? "0" + s : s)
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
                activeTab: activeSection
                onTabClicked: function(i) { activeSection = i }
                onMinimizeClicked: app.showMinimized()
                onCloseClicked: Qt.quit()
            }

            Item {
                width: parent.width
                height: parent.height - topBar.height - 72

                // ===== DASHBOARD (Section 0) =====
                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    visible: activeSection === 0

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: dashCol.height + 60
                        clip: true
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
                                        if (backend) { backend.startSplit(path); activeSection = 1 }
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
                                            Text { text: "\uE889"; font.family: "Material Symbols Outlined"; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Recent Separations"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                                        }

                                        ListView {
                                            id: historyList
                                            width: parent.width
                                            height: parent.height - 55
                                            interactive: false
                                            model: backend ? backend.historyModel : null
                                            delegate: Item {
                                                width: parent.width; height: 44
                                                Rectangle { id: histIcon; x: 4; y: 4; width: 36; height: 36; radius: 8; color: Qt.rgba(0,0.89,0.53,0.08)
                                                    Text { anchors.centerIn: parent; text: "\uE40B"; font.family: "Material Symbols Outlined"; color: "#00e388"; font.pixelSize: 16 }
                                                }
                                                Row { id: histActions; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; anchors.rightMargin: 4; spacing: 8
                                                    Text { text: "\uE037"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.4); font.pixelSize: 14 }
                                                    Text { text: "\uE2C4"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.4); font.pixelSize: 14 }
                                                }
                                                Column { anchors.verticalCenter: parent.verticalCenter; anchors.left: histIcon.right; anchors.leftMargin: 12; anchors.right: histActions.left; anchors.rightMargin: 8
                                                    Text { text: model.file_name || ""; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 14; font.weight: Font.Medium; elide: Text.ElideMiddle; width: parent.width }
                                                    Row { spacing: 4
                                                        Text { text: model.status === "ok" ? (model.stems || "6 Stems") : ""; color: Qt.rgba(0.73,0.8,0.73,0.4); font.family: "Inter"; font.pixelSize: 11 }
                                                        Text { text: (model.status === "ok" && model.created_at) ? "\u2022" : ""; color: Qt.rgba(0.73,0.8,0.73,0.3); font.family: "Inter"; font.pixelSize: 11 }
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
                    anchors.fill: parent
                    color: "transparent"
                    visible: activeSection === 1

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: procCol.height + 60
                        clip: true
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

                                        Row { spacing: 12
                                            Button { flat: true
                                                background: Rectangle { radius: 8; color: parent.hovered ? Qt.rgba(1,1,1,0.06) : Qt.rgba(1,1,1,0.02); border.color: Qt.rgba(1,1,1,0.08); border.width: 1 }
                                                contentItem: Text { text: "Pause"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.Medium; leftPadding: 16; rightPadding: 16 }
                                            }
                                            Button { flat: true
                                                background: Rectangle { radius: 8; color: parent.hovered ? Qt.rgba(0.93,0,0.03,0.1) : Qt.rgba(0.93,0,0.03,0.04); border.color: Qt.rgba(0.93,0,0.03,0.15); border.width: 1 }
                                                contentItem: Text { text: "Cancel"; color: "#ffb4ab"; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.Medium; leftPadding: 16; rightPadding: 16 }
                                                onClicked: { if (backend) backend.cancelSplit(); activeSection = 0 }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ===== STEM MIXER (Section 2) =====
                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    visible: activeSection === 2

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: mixCol.height + 60
                        clip: true
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
                                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; height: 44; radius: 12; color: "#00e388"
                                    Row { anchors.centerIn: parent; spacing: 6; leftPadding: 20; rightPadding: 20
                                        Text { text: "\uE2C4"; font.family: "Material Symbols Outlined"; color: "#00391e"; font.pixelSize: 16; anchors.verticalCenter: parent.verticalCenter }
                                        Text { text: "Export All"; color: "#00391e"; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true; onClicked: { if (audioEngine) audioEngine.exportAllStems() } }
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
                                    accentColor: ({
                                        "vocals":"#FF69B4",
                                        "drums":"#4FC3F7",
                                        "bass":"#FFD700",
                                        "other":"#00e388"
                                    })[modelData.name.toLowerCase()] || "#00e388"
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
                                                Text { anchors.centerIn: parent; text: modelData.icon; font.family: "Material Symbols Outlined"; font.pixelSize: 20 }
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
                    anchors.fill: parent
                    color: "transparent"
                    visible: activeSection === 3

                    Flickable {
                        anchors.fill: parent
                        anchors.margins: 32
                        contentHeight: setCol.height + 60
                        clip: true
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
                                            Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "\uE322"; font.family: "Material Symbols Outlined"; font.pixelSize: 20 }
                                        }
                                        Rectangle { width: parent.width; height: 52; radius: 10; color: Qt.rgba(0,0.89,0.53,0.04); border.color: Qt.rgba(0,0.89,0.53,0.25); border.width: 1
                                            Item { anchors.fill: parent; anchors.margins: 16
                                                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                                    Text { text: "NVIDIA CUDA (GPU)"; color: "#00e388"; font.family: "Inter"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                                    Text { text: "Recommended for batch processing"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 11 }
                                                }
                                                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 18; height: 18; radius: 9; color: "#00e388"
                                                    Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: "#121414" }
                                                }
                                            }
                                        }
                                        Rectangle { width: parent.width; height: 52; radius: 10; color: "transparent"; border.color: Qt.rgba(1,1,1,0.06); border.width: 1
                                            Item { anchors.fill: parent; anchors.margins: 16
                                                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                                    Text { text: "CPU Cluster"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.family: "Inter"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                                    Text { text: "Standard high-precision threads"; color: Qt.rgba(0.73,0.8,0.73,0.35); font.family: "Inter"; font.pixelSize: 11 }
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle { width: (parent.width - 24) * 0.48; height: 330; radius: 24; color: Qt.rgba(1,1,1,0.03); border.color: Qt.rgba(1,1,1,0.08); border.width: 1
                                    Column { anchors.fill: parent; anchors.margins: 20; spacing: 18
                                        Item { width: parent.width; height: 24
                                            Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: "Demucs Configuration"; color: "#e2e2e2"; font.family: "Inter"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                            Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "\uE322"; font.family: "Material Symbols Outlined"; font.pixelSize: 20 }
                                        }
                                        Column { width: parent.width; spacing: 6
                                            Text { text: "Model"; color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 12 }
                                            ModernCombo {
                                                id: modelBox
                                                width: parent.width
                                                model: ["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_extra"]
                                                currentIndex: 0
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
                                                value: 10
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
                            }
                        }
                    }
                }
            }

            // ===== BOTTOM PLAYER BAR =====
            Rectangle {
                width: parent.width
                height: 72
                color: Qt.rgba(0.12, 0.12, 0.12, 0.85)

                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: 1
                    color: Qt.rgba(1, 1, 1, 0.08)
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 32
                    anchors.rightMargin: 32

                    Item {
                        width: parent.width * 0.3
                        height: parent.height
                        Row { anchors.verticalCenter: parent.verticalCenter; spacing: 10
                            Text { text: currentStems.length > 0 ? currentStems[0].name : ""; color: "#00e388"; font.family: "Inter"; font.pixelSize: 11; font.letterSpacing: 1; font.weight: Font.Medium; visible: currentStems.length > 0 }
                            Text { text: formatTime(audioEngine ? audioEngine.position : 0); color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 11 }
                            NeoSlider {
                                id: progressSlider
                                width: 200
                                anchors.verticalCenter: parent.verticalCenter
                                from: 0
                                to: audioEngine ? audioEngine.duration : 100
                                value: audioEngine ? audioEngine.position : 0
                                accent: "#00e388"
                                onPressedChanged: {
                                    if (!pressed && audioEngine) audioEngine.seek(value)
                                }
                            }
                            Text { text: formatTime(audioEngine ? audioEngine.duration : 0); color: Qt.rgba(0.73,0.8,0.73,0.55); font.family: "Inter"; font.pixelSize: 11 }
                        }
                    }

                    Item {
                        width: parent.width * 0.4
                        height: parent.height
                        Row { anchors.centerIn: parent; spacing: 14
                            MediaButton {
                                icon: "\uE043"
                            }
                            MediaButton {
                                icon: "\uE045"
                                onClicked: {
                                    if (audioEngine) audioEngine.previous()
                                }
                            }
                                Rectangle {
                                id: playBtn
                                width: 58
                                height: 58
                                radius: 29
                                property bool playing: false
                                color: playing
                                       ? "#FF4D6D"
                                       : playMouse.containsMouse
                                            ? "#14f19b"
                                            : "#00e388"
                                Behavior on color { ColorAnimation { duration: 120 } }
                                Text {
                                    anchors.centerIn: parent
                                    text: playBtn.playing ? "\uE034" : "\uE037"
                                    font.family: "Material Symbols Outlined"
                                    color: "#00391e"
                                    font.pixelSize: 30
                                }
                                Connections {
                                    target: audioEngine
                                    function onAllPlayingChanged() {
                                        playBtn.playing = audioEngine.allPlaying
                                    }
                                }
                                MouseArea {
                                    id: playMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (audioEngine) audioEngine.togglePlayAll()
                                    }
                                }
                            }
                            MediaButton {
                                icon: "\uE044"
                                onClicked: {
                                    if (audioEngine) audioEngine.next()
                                }
                            }
                            MediaButton {
                                icon: "\uE040"
                                active: true
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
                            Text { text: "\uE8B8"; font.family: "Material Symbols Outlined"; color: Qt.rgba(0.73,0.8,0.73,0.45); font.pixelSize: 20; anchors.verticalCenter: parent.verticalCenter; MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: activeSection = 3 } }
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
        function onSplitStarted(fp) { currentStems = []; activeSection = 1; if (audioEngine) audioEngine.clearAll() }
        function onProgressUpdated(v) { app.procProgress = Math.min(v, 99) }
        function onStatusUpdated(msg) { statusLabel.text = msg }
        function onWaveformReady(name, data) { wavePanel.waveformData = data; wavePanel.hasAudio = true }
        function onSplitFinished(status, stemsJson) {
            var stems = JSON.parse(stemsJson)
            if (status === "ok") {
                currentStems = stems; activeSection = 2
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

    Component.onCompleted: {
        if (backend) {
            backend.checkGpu()
            demucsCheck.start()
        }
    }
}
