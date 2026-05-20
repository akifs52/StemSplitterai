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
            width: parent.width - 120 - 200 - 20
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
            width: 180
            height: parent.height

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "GAIN"
                        color: Qt.rgba(0.73, 0.8, 0.73, 0.45)
                        font.family: "Inter"
                        font.pixelSize: 10
                        font.letterSpacing: 1.2
                        font.weight: Font.Medium
                    }

                    Rectangle {
                        width: 90
                        height: 4
                        radius: 2
                        color: Qt.rgba(1, 1, 1, 0.08)

                        Rectangle {
                            width: gainSlider.position * parent.width
                            height: parent.height
                            radius: 2
                            color: root.accentColor
                        }

                        Slider {
                            id: gainSlider
                            anchors.fill: parent
                            from: 0
                            to: 1
                            value: root.gainValue
                            leftPadding: 0
                            rightPadding: 0
                            topPadding: -6
                            bottomPadding: -6

                            background: Item {}

                            handle: Rectangle {
                                x: gainSlider.leftPadding + gainSlider.visualPosition * (gainSlider.availableWidth - width)
                                y: (gainSlider.availableHeight - height) / 2
                                width: 12
                                height: 12
                                radius: 2
                                color: root.accentColor

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 2
                                    color: root.accentColor
                                    opacity: 0.25
                                    scale: 1.6
                                    visible: gainSlider.pressed || ma.containsMouse
                                }
                            }

                            onMoved: root.gainAdjusted(gainSlider.value)

                            MouseArea {
                                id: ma
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                            }
                        }
                    }
                }

                Row {
                    spacing: 8

                    Button {
                        width: 36
                        height: 36
                        flat: true
                        background: Rectangle {
                            radius: 8
                            color: parent.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
                            border.color: Qt.rgba(1, 1, 1, 0.06)
                            border.width: 1
                        }
                        contentItem: Text {
                            text: "M"
                            color: root.isMuted ? "#ffb4ab" : Qt.rgba(0.73, 0.8, 0.73, 0.6)
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: root.muteClicked()
                    }

                    Button {
                        width: 36
                        height: 36
                        flat: true
                        background: Rectangle {
                            radius: 8
                            color: parent.hovered ? Qt.rgba(0, 0.89, 0.53, 0.08) : "transparent"
                            border.color: Qt.rgba(1, 1, 1, 0.06)
                            border.width: 1
                        }
                        contentItem: Text {
                            text: "S"
                            color: root.isSolo ? "#00e388" : Qt.rgba(0.73, 0.8, 0.73, 0.6)
                            font.pixelSize: 13
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: root.soloClicked()
                    }

                    Button {
                        width: 36
                        height: 36
                        flat: true
                        background: Rectangle {
                            radius: 8
                            color: parent.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
                            border.color: Qt.rgba(1, 1, 1, 0.06)
                            border.width: 1
                        }
                        contentItem: Text {
                            text: "\uE2C4"; font.family: "Material Symbols Outlined"
                            color: Qt.rgba(0.73, 0.8, 0.73, 0.6)
                            font.pixelSize: 14
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: root.downloadClicked()
                    }
                }
            }
        }
    }
}
