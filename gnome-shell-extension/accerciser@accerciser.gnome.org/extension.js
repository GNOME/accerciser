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
    // https://gjs-docs.gnome.org/meta16~16-windowactor/
    // https://gjs-docs.gnome.org/meta16~16/meta.window
    let window_infos = [];
    const activeWorkspace = global.workspace_manager.get_active_workspace();
    const windows = global.get_window_actors();
    for (let i = 0; i < windows.length; i++)
    {
        let window = windows[i].metaWindow;
        const isOnActiveWorkspace = window.located_on_workspace(activeWorkspace);

        let geometry = null;
        // meta_window_get_client_content_rect available from GNOME/Mutter 47 on
        if (window.get_client_content_rect)
        {
            geometry = window.get_client_content_rect();
        }
        else
        {
            // for GNOME/Mutter 46, convert frame rect to client rect if the
            // window doesn't have client side decorations
            geometry = window.get_frame_rect();
            if (window.is_client_decorated && !window.is_client_decorated())
                geometry = window.frame_rect_to_client_rect(geometry);
        }

        window_infos.push(
            {
            "caption": window.title,
            "bufferGeometry.x": window.get_buffer_rect().x,
            "bufferGeometry.y": window.get_buffer_rect().y,
            "bufferGeometry.width": window.get_buffer_rect().width,
            "bufferGeometry.height": window.get_buffer_rect().height,
            "geometry.x": geometry.x,
            "geometry.y": geometry.y,
            "geometry.width": geometry.width,
            "geometry.height": geometry.height,
            "gtk_application_id":  window.get_gtk_application_id(),
            "isOnCurrentWorkspace": isOnActiveWorkspace,
            "pid": window.get_pid(),
            "sandboxed_app_id": window.get_sandboxed_app_id()
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
    <method name="GetMousePosition">
      <arg type="u" direction="out" name="x"/>
      <arg type="u" direction="out" name="y"/>
  </method>
  </interface>
</node>`;


// implements the methods defined in the XML description above
class DBusService {
    GetMousePosition() {
        const pointer = global.get_pointer();
        const x = pointer[0];
        const y = pointer[1];
        return [x, y];
    }

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
