import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

Item {
    id: root

    signal fileDropped(string path)

    property bool hovered: false

    Rectangle {
        anchors.fill: parent
        radius: 32

        color: root.hovered ? Qt.rgba(0, 0.89, 0.53, 0.04) : "transparent"
        border.color: root.hovered ? "#00e388" : Qt.rgba(1, 1, 1, 0.15)
        border.width: 2

        Behavior on border.color { ColorAnimation { duration: 250 } }
        Behavior on color { ColorAnimation { duration: 250 } }

        Column {
            anchors.centerIn: parent
            spacing: 20

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 72
                height: 72
                radius: 36
                color: Qt.rgba(0, 0.89, 0.53, 0.12)

                Text {
                    anchors.centerIn: parent
                    text: "\uE2C6"
                    font.family: "Material Symbols Outlined"
                    color: "#00e388"
                    font.pixelSize: 32
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.hovered ? "Drop Audio File" : "Drag && Drop Audio"
                color: root.hovered ? "#00e388" : Qt.rgba(0.88, 0.88, 0.88, 0.85)
                font.family: "Montserrat"
                font.pixelSize: 22
                font.weight: Font.DemiBold
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "MP3, WAV, FLAC or OGG up to 500MB"
                color: Qt.rgba(0.73, 0.8, 0.73, 0.5)
                font.family: "Inter"
                font.pixelSize: 14
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: browseTxt.width + 48
                height: 44
                radius: 12
                color: "#00e388"

                Text {
                    id: browseTxt
                    anchors.centerIn: parent
                    text: "Browse Files"
                    color: "#00391e"
                    font.family: "Inter"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: fileDialog.open()
                }
            }
        }

        DropArea {
            anchors.fill: parent
            onEntered: { drag.accepted = true; root.hovered = true }
            onExited: root.hovered = false
            onDropped: {
                root.hovered = false
                if (drop.urls.length > 0) {
                    var path = decodeURIComponent(drop.urls[0].toString())
                    if (path.startsWith("file:///"))
                        path = path.substring(8)
                    else if (path.startsWith("file://"))
                        path = path.substring(7)
                    root.fileDropped(path)
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "Select Audio File"
        nameFilters: ["Audio Files (*.wav *.mp3 *.flac *.m4a *.ogg)", "All Files (*)"]
        onAccepted: {
            var path = decodeURIComponent(fileDialog.selectedFile.toString())
            if (path.startsWith("file:///"))
                path = path.substring(8)
            else if (path.startsWith("file://"))
                path = path.substring(7)
            root.fileDropped(path)
        }
    }
}
