import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string stemName: "Vocals"
    property string stemLabel: "STEM 01"
    property string accentColor: "#FF69B4"
    property real gainValue: 0.85
    property bool isMuted: false
    property bool isSolo: false
    property string stemId: ""

    signal muteClicked()
    signal soloClicked()
    signal downloadClicked()
    signal gainAdjusted(real value)

    width: parent ? parent.width : 600
    height: 88
    radius: 16
    color: Qt.rgba(1, 1, 1, 0.03)
    border.color: Qt.rgba(1, 1, 1, 0.06)
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 16
        spacing: 20

        Item {
            width: 120
            height: parent.height

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    text: root.stemLabel
                    color: root.accentColor
                    font.family: "Inter"
                    font.pixelSize: 11
                    font.letterSpacing: 1.2
                    font.weight: Font.Medium
                }

                Text {
                    text: root.stemName
                    color: "#e2e2e2"
                    font.family: "Montserrat"
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                }
            }
        }

        Item {
            width: parent.width - 120 - 280 - 20
            height: parent.height

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                height: 64
                radius: 8
                color: Qt.rgba(1, 1, 1, 0.02)
                clip: true

                Row {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 2

                    Repeater {
                        model: 50
                        delegate: Rectangle {
                            readonly property real h: 0.15 + Math.random() * 0.7
                            width: (parent.width - 49 * 2) / 50
                            height: parent.height * h
                            anchors.bottom: parent.bottom
                            color: root.accentColor
                            opacity: 0.5 + Math.random() * 0.5
                            radius: 1
                        }
                    }
                }
            }
        }

        Item {
            width: 260
            height: parent.height

            Row {
                anchors.fill: parent
                anchors.verticalCenter: parent.verticalCenter
                spacing: 20

                Column {
                    width: 130
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Text {
                        text: "GAIN"
                        color: Qt.rgba(0.73, 0.8, 0.73, 0.45)
                        font.family: "Inter"
                        font.pixelSize: 10
                        font.letterSpacing: 1.2
                        font.weight: Font.Medium
                    }

                    NeoSlider {
                        id: gainSlider
                        width: parent.width
                        from: 0
                        to: 100
                        value: 80
                        accent: root.accentColor

                        onValueChanged: {
                            gainAdjusted(value / 100.0)
                        }
                    }
                }

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Rectangle {
                        id: muteBtn
                        width: 34
                        height: 34
                        radius: 9

                        color: root.isMuted
                               ? "#FF4D6D"
                               : ma1.containsMouse
                                 ? Qt.rgba(1,1,1,0.08)
                                 : Qt.rgba(1,1,1,0.04)

                        border.color: root.isMuted
                                      ? "#FF8FA3"
                                      : Qt.rgba(1,1,1,0.08)

                        border.width: 1

                        scale: ma1.pressed ? 0.92 : 1.0

                        Behavior on scale { NumberAnimation { duration: 90 } }
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Text {
                            anchors.centerIn: parent
                            text: "M"
                            color: root.isMuted ? "white" : "#d9d9d9"
                            font.bold: true
                            font.pixelSize: 12
                        }

                        MouseArea {
                            id: ma1
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.muteClicked()
                        }
                    }

                    Rectangle {
                        id: soloBtn
                        width: 34
                        height: 34
                        radius: 9

                        color: root.isSolo
                               ? "#00F5A0"
                               : ma2.containsMouse
                                 ? Qt.rgba(1,1,1,0.08)
                                 : Qt.rgba(1,1,1,0.04)

                        border.color: root.isSolo
                                      ? "#B6FFD9"
                                      : Qt.rgba(1,1,1,0.08)

                        border.width: 1

                        scale: ma2.pressed ? 0.92 : 1.0

                        Behavior on scale { NumberAnimation { duration: 90 } }
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Text {
                            anchors.centerIn: parent
                            text: "S"
                            color: root.isSolo ? "white" : "#d9d9d9"
                            font.bold: true
                            font.pixelSize: 12
                        }

                        MouseArea {
                            id: ma2
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.soloClicked()
                        }
                    }

                    Rectangle {
                        id: downloadBtn
                        width: 34
                        height: 34
                        radius: 9

                        color: ma3.containsMouse
                               ? Qt.rgba(1,1,1,0.08)
                               : Qt.rgba(1,1,1,0.04)

                        border.color: Qt.rgba(1,1,1,0.08)
                        border.width: 1

                        scale: ma3.pressed ? 0.92 : 1.0

                        Behavior on scale { NumberAnimation { duration: 90 } }
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Text {
                            anchors.centerIn: parent
                            text: "\uE2C4"
                            font.family: "Material Symbols Outlined"
                            color: "#d9d9d9"
                            font.pixelSize: 13
                        }

                        MouseArea {
                            id: ma3
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.downloadClicked()
                        }
                    }
                }
            }
        }
    }
}
