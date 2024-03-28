/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

import Gio from 'gi://Gio';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';


function collectWindowInfos() {
    // API doc:
    // https://gjs-docs.gnome.org/meta14~14-windowactor/
    // https://gjs-docs.gnome.org/meta14~14/meta.window
    let window_infos = [];
    const windows = global.get_window_actors();
    for (let i = 0; i < windows.length; i++)
    {
        let window = windows[i].metaWindow;
        window_infos.push(
            {
            "caption": window.title,
            "bufferGeometry.x": window.get_buffer_rect().x,
            "bufferGeometry.y": window.get_buffer_rect().y,
            "bufferGeometry.width": window.get_buffer_rect().width,
            "bufferGeometry.height": window.get_buffer_rect().height
            }
        );
    }
    const json_output = JSON.stringify(window_infos);
    return json_output;
}


const interfaceXml = `
<node>
  <interface name="org.gnome.accerciser.Accerciser">
    <method name="GetWindowInfos">
      <arg type="s" direction="out" name="window_infos"/>
    </method>
  </interface>
</node>`;


// implements the methods defined in the XML description above
class DBusService {
    GetWindowInfos() {
        return collectWindowInfos();
    }
}


let dBusServiceInstance = null;
let dBusExportedObject = null;

function onBusAcquired(connection, _name) {
    dBusServiceInstance = new DBusService();
    dBusExportedObject = Gio.DBusExportedObject.wrapJSObject(interfaceXml,
        dBusServiceInstance);
    dBusExportedObject.export(connection, '/org/gnome/accerciser/Accerciser');
}

function onNameAcquired(_connection, _name) {
}

function onNameLost(_connection, _name) {
}


export default class AccerciserExtension extends Extension {
    enable() {
        let ownerId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            'org.gnome.accerciser.Accerciser',
            Gio.BusNameOwnerFlags.NONE,
            onBusAcquired,
            onNameAcquired,
            onNameLost);
        this.dbusOwnerId = ownerId;
    }

    disable() {
        if (this.dbusOwnerId)
            Gio.bus_unown_name(this.dbusOwnerId);
    }
}
