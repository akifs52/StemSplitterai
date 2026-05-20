import QtQuick
import QtQuick.Controls

Slider {
    id: control

    property color accent: "#00e388"

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: Qt.rgba(1, 1, 1, 0.06)

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: control.accent
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: 14
        height: 14
        radius: 7
        color: control.accent

        Rectangle {
            anchors.fill: parent
            radius: 7
            color: control.accent
            opacity: 0.25
            scale: 1.6
            visible: control.pressed || handleMouse.containsMouse
        }

        MouseArea {
            id: handleMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }
    }
}
