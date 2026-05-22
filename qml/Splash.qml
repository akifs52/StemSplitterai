import QtQuick
import QtQuick.Window
import Qt5Compat.GraphicalEffects

Window {
    id: splash

    width: 800
    height: 600
    visible: true
    color: "#000000"
    flags: Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

    property string statusText: "Initializing AI Engine..."
    property real progressValue: 0.0

    FontLoader { id: montserratBold; source: "../assets/fonts/Montserrat-Bold.ttf" }
    FontLoader { id: interMedium; source: "../assets/fonts/Inter-Medium.ttf" }
    FontLoader { id: interSemiBold; source: "../assets/fonts/Inter-SemiBold.ttf" }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        clip: true

        Image {
            id: bgSource
            anchors.fill: parent
            source: "../assets/icons/icon.png"
            fillMode: Image.PreserveAspectFit
            visible: false
            scale: 1.02
        }

        FastBlur {
            id: blurredBackground
            anchors.fill: parent
            source: bgSource
            radius: 5
            opacity: 0.56
            scale: 1.02

            NumberAnimation on scale {
                from: 1.02
                to: 1.055
                duration: 10000
                easing.type: Easing.OutQuad
                running: splash.visible
            }
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0.14) }
                GradientStop { position: 0.55; color: Qt.rgba(0, 0, 0, 0.08) }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.48) }
            }
        }

        DropShadow {
            anchors.fill: card
            horizontalOffset: 0
            verticalOffset: 24
            radius: 34
            samples: 48
            color: Qt.rgba(0, 0, 0, 0.34)
            source: card
        }

        Rectangle {
            id: card
            anchors.centerIn: parent
            width: 254
            height: 120
            radius: 3
            color: Qt.rgba(0x10 / 255, 0x13 / 255, 0x13 / 255, 0.42)
            border.color: Qt.rgba(1, 1, 1, 0.018)
            border.width: 1

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: Qt.rgba(1, 1, 1, 0.012)
            }

            Column {
                anchors.fill: parent
                anchors.leftMargin: 31
                anchors.rightMargin: 31
                anchors.topMargin: 28
                anchors.bottomMargin: 30
                spacing: 0

                Item {
                    width: parent.width
                    height: 40

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 0

                        Text {
                            text: "Stem"
                            color: "#e2e2e2"
                            font.family: montserratBold.name
                            font.pixelSize: 25
                            font.bold: true
                            lineHeight: 1.1
                        }

                        Text {
                            text: "Split"
                            color: "#e2e2e2"
                            font.family: montserratBold.name
                            font.pixelSize: 25
                            font.bold: true
                            lineHeight: 1.1
                        }

                        Text {
                            id: aiText
                            text: "AI"
                            color: "#00e388"
                            font.family: montserratBold.name
                            font.pixelSize: 25
                            font.bold: true
                            lineHeight: 1.1

                            layer.enabled: true
                            layer.effect: Glow {
                                color: Qt.rgba(0, 0.89, 0.53, 0.62)
                                radius: 10
                                samples: 20
                            }
                        }
                    }
                }

                Item {
                    width: parent.width
                    height: 14
                }

                Column {
                    width: parent.width
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 4

                    Row {
                        width: parent.width
                        height: 8

                        Text {
                            width: parent.width - 46
                            anchors.bottom: parent.bottom
                            text: splash.statusText
                            color: Qt.rgba(0.73, 0.80, 0.73, 0.80)
                            font.family: interMedium.name
                            font.pixelSize: 6
                            font.weight: Font.Medium
                            font.capitalization: Font.AllUppercase
                            elide: Text.ElideRight
                        }

                        Text {
                            width: 46
                            anchors.bottom: parent.bottom
                            horizontalAlignment: Text.AlignRight
                            text: {
                                if (splash.progressValue >= 1.0)
                                    return "READY"
                                var pct = Math.round(splash.progressValue * 100)
                                return (pct < 10 ? "0" : "") + pct + "%"
                            }
                            color: splash.progressValue >= 1.0 ? "#e2e2e2" : "#00e388"
                            font.family: interSemiBold.name
                            font.pixelSize: 6
                            font.weight: Font.DemiBold
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        radius: 1
                        color: Qt.rgba(1, 1, 1, 0.14)
                        clip: true

                        Rectangle {
                            id: progressFill
                            width: parent.width * Math.max(0.0, Math.min(1.0, splash.progressValue))
                            height: parent.height
                            radius: 1
                            color: "#00e388"

                            Behavior on width {
                                NumberAnimation { duration: 400; easing.type: Easing.OutCubic }
                            }

                            layer.enabled: true
                            layer.effect: Glow {
                                color: Qt.rgba(0, 0.89, 0.53, splash.progressValue >= 1.0 ? 0.90 : 0.60)
                                radius: splash.progressValue >= 1.0 ? 10 : 6
                                samples: 18
                            }
                        }
                    }
                }
            }
        }

        Text {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 21
            anchors.bottomMargin: 14
            text: "VERSION 1.0.0"
            color: Qt.rgba(0.73, 0.80, 0.73, 0.40)
            font.family: interSemiBold.name
            font.pixelSize: 6
            font.weight: Font.DemiBold
            font.letterSpacing: 1.5
        }
    }

    SequentialAnimation on progressValue {
        running: splash.visible
        NumberAnimation { to: 0.72; duration: 1400; easing.type: Easing.OutCubic }
        NumberAnimation { to: 0.88; duration: 1200; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0.94; duration: 900; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.OutQuad }
    }

    function setStatus(text, value) {
        statusText = text
        if (value !== undefined)
            progressValue = value
    }
}
