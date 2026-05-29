import QtQuick

Rectangle {
    id: root

    property color glassColor: Qt.rgba(1, 1, 1, 0.03)
    property color borderColor: Qt.rgba(1, 1, 1, 0.1)
    property real cardRadius: 24

    radius: cardRadius
    color: glassColor
    border.color: borderColor
    border.width: 1

    layer.enabled: true
    layer.samples: 4
}
