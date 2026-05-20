import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Rectangle {
    id: root

    property string gpuInfo: "CPU Mode"
    property bool gpuAvailable: false
    property int activeTab: 0

    signal tabClicked(int index)
    signal minimizeClicked()
    signal closeClicked()

    height: 64
    width: parent ? parent.width : 1400
    color: Qt.rgba(0.07, 0.08, 0.08, 0.8)

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Qt.rgba(1, 1, 1, 0.1)
    }

    MouseArea {
        anchors.fill: parent
        property point clickPos: Qt.point(0, 0)
        onPressed: function(mouse) { clickPos = Qt.point(mouse.x, mouse.y) }
        onPositionChanged: function(mouse) {
            if (pressed) {
                var w = root.Window.window
                if (w) {
                    w.x += mouse.x - clickPos.x
                    w.y += mouse.y - clickPos.y
                }
            }
        }
        cursorShape: Qt.OpenHandCursor
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 32
        anchors.rightMargin: 16
        spacing: 40

        Text {
            text: "SonicSplit AI"
            color: "#00e388"
            font.family: "Montserrat"
            font.pixelSize: 22
            font.weight: Font.Bold
            font.letterSpacing: -0.5
            Layout.alignment: Qt.AlignVCenter
        }

        RowLayout {
            spacing: 24
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: ["Dashboard", "Processing", "Stem Mixer", "Settings"]
                delegate: Item {
                    id: delItem
                    property bool isActive: index === root.activeTab
                    Layout.fillHeight: true
                    Layout.preferredWidth: txt.implicitWidth + 4

                    Text {
                        id: txt
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        color: delItem.isActive ? "#e2e2e2" : Qt.rgba(0.73, 0.8, 0.73, 0.5)
                        font.family: "Inter"
                        font.pixelSize: 14
                        font.weight: delItem.isActive ? Font.Medium : Font.Normal
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 0
                        width: txt.width
                        height: 2
                        radius: 1
                        color: "#00e388"
                        visible: delItem.isActive
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: { if (!delItem.isActive) txt.color = Qt.rgba(0.73, 0.8, 0.73, 0.8) }
                        onExited: { if (!delItem.isActive) txt.color = Qt.rgba(0.73, 0.8, 0.73, 0.5) }
                        onClicked: root.tabClicked(index)
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }

        RowLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: 16

            Rectangle {
                height: 28
                Layout.fillWidth: false
                radius: 14
                color: root.gpuAvailable ? Qt.rgba(0, 0.89, 0.53, 0.1) : Qt.rgba(1, 1, 1, 0.04)
                border.color: root.gpuAvailable ? Qt.rgba(0, 0.89, 0.53, 0.3) : Qt.rgba(1, 1, 1, 0.06)
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 6
                    leftPadding: 10
                    rightPadding: 10

                    Item {
                        width: 8
                        height: 8
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            width: 8; height: 8; radius: 4; color: root.gpuAvailable ? "#00e388" : "#FFD600"
                        }
                        Rectangle {
                            width: 8; height: 8; radius: 4; color: root.gpuAvailable ? "#00e388" : "#FFD600"
                            opacity: 0.3; scale: 1.6; visible: root.gpuAvailable
                        }
                    }

                    Text {
                        text: root.gpuAvailable ? "GPU" : "CPU"
                        color: root.gpuAvailable ? "#00e388" : "#FFD600"
                        font.family: "Inter"
                        font.pixelSize: 11
                        font.letterSpacing: 0.8
                        anchors.verticalCenter: parent.verticalCenter
                        font.weight: Font.Medium
                    }
                }
            }

            Repeater {
                model: ["\uE322", "\uE7F4"]
                delegate: Rectangle {
                    width: 32; height: 32; radius: 8
                    color: ma.containsMouse ? Qt.rgba(1,1,1,0.05) : "transparent"
                    Text { anchors.centerIn: parent; text: modelData; font.family: "Material Symbols Outlined"; font.pixelSize: 16 }
                    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor }
                }
            }

            Rectangle {
                width: 32; height: 32; radius: 16; color: "transparent"
                border.color: Qt.rgba(1,1,1,0.15); border.width: 1
                Text { anchors.centerIn: parent; text: "\uE853"; font.family: "Material Symbols Outlined"; font.pixelSize: 16 }
            }

            Rectangle { width: 1; height: 20; color: Qt.rgba(1,1,1,0.08) }

            Button {
                width: 28; height: 28; flat: true
                background: Rectangle { radius: 6; color: parent.hovered ? Qt.rgba(1,1,1,0.06) : "transparent" }
                contentItem: Text { text: "\u2014"; color: Qt.rgba(0.73,0.8,0.73,0.6); font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: root.minimizeClicked()
            }

            Button {
                width: 28; height: 28; flat: true
                background: Rectangle { radius: 6; color: parent.hovered ? Qt.rgba(1,0.32,0.32,0.12) : "transparent" }
                contentItem: Text { text: "\u2715"; color: parent.hovered ? "#ffb4ab" : Qt.rgba(0.73,0.8,0.73,0.6); font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: root.closeClicked()
            }
        }
    }
}
