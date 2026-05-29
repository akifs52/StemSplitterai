import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string icon: ""
    property color iconColor: "#b7c5b7"
    property color hoverColor: Qt.rgba(1,1,1,0.06)
    property color pressedColor: Qt.rgba(1,1,1,0.12)
    property bool active: false
    signal clicked()

    width: 40
    height: 40
    radius: width / 2

    color: {
        if (mouse.pressed)
            return pressedColor

        if (mouse.containsMouse)
            return hoverColor

        if (active)
            return Qt.rgba(0,0.89,0.53,0.12)

        return "transparent"
    }

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    Text {
        anchors.centerIn: parent
        text: root.icon
        font.family: "Material Symbols Outlined"
        font.pixelSize: 22

        color: {
            if (root.active)
                return "#00e388"

            if (mouse.containsMouse)
                return "#ffffff"

            return root.iconColor
        }

        Behavior on color {
            ColorAnimation { duration: 120 }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onClicked: root.clicked()
    }
}
