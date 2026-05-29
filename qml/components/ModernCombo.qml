import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    implicitWidth: 320
    implicitHeight: 42
    font.family: "Inter"
    font.pixelSize: 14

    delegate: ItemDelegate {
        width: control.width
        height: 40
        contentItem: Text {
            text: modelData
            color: "#EAEAEA"
            font: control.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: hovered ? "#1E2422" : "#151818"
        }
    }

    indicator: Canvas {
        x: control.width - width - 18
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 12
        height: 8
        contextType: "2d"
        onPaint: {
            context.reset()
            context.moveTo(0, 0)
            context.lineTo(width, 0)
            context.lineTo(width / 2, height)
            context.closePath()
            context.fillStyle = "#00F5A0"
            context.fill()
        }
    }

    contentItem: Text {
        leftPadding: 16
        rightPadding: control.indicator.width + 24
        text: control.displayText
        font: control.font
        color: "#F5F5F5"
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 14
        color: "#161919"
        border.color: control.focus ? "#00F5A0" : "#2B2E2E"
        border.width: 1
        layer.enabled: true
        smooth: true
    }

    popup: Popup {
        y: control.height + 8
        width: control.width
        implicitHeight: contentItem.implicitHeight
        padding: 6
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 }
        }
        background: Rectangle {
            radius: 16
            color: "#141616"
            border.color: "#2B2E2E"
            layer.enabled: true
            smooth: true
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
        }
    }
}
