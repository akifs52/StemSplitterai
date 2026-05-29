import QtQuick
import QtQuick.Controls

Slider {
    id: control
    implicitWidth: 280
    implicitHeight: 26
    from: 0
    to: 100

    background: Item {
        y: control.height / 2 - 2
        width: control.availableWidth
        height: 4

        Rectangle {
            anchors.fill: parent
            radius: 2
            color: "#242828"
        }
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: "#00F5A0"
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.height / 2 - height / 2
        width: 18
        height: 18
        radius: 9
        color: "#00F5A0"
        border.color: "#B6FFD9"
        border.width: 1
        layer.enabled: true
        smooth: true
    }
}
