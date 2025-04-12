const asyncHandler = require("express-async-handler");
const Contact = require("../models/contactModel");

//@desc Get all contacts
//@route GET /apu/contacts
//@access public

const getContacts = asyncHandler(async (req,res) => {
    const contacts = await Contact.find();
    res.status(200).json(contacts);
});

//@desc Create new contacts
//@route POST /apu/contacts
//@access public

const createContact = asyncHandler(async(req,res) => {
    console.log("The request body is :", req.body);
    const {name, email, phone} = req.body;
    if(!name || !email || !phone){
        res.status(400);
        throw new Error("All field are mandatory !");
    }
    res.status(201).json({message :"Creat Contact"});
});

//@desc Get contacts
//@route GET /apu/contacts/:id
//@access public

const getContact = asyncHandler(async(req,res) => {
    res.status(200).json({message :`Get contact for ${req.params.id} `});
});

//@desc Update new contacts
//@route PUT /apu/contacts/:id
//@access public

const updateContact = asyncHandler(async (req,res) => {
    res.status(200).json({message :`Update contact for ${req.params.id} `});
});

//@desc Delete new contacts
//@route DELETE /apu/contacts/:id
//@access public

const deleteContact = asyncHandler(async (req,res) => {
    res.status(200).json({message :`Delete contact for ${req.params.id} `});
});


module.exports = {
    getContacts,
    createContact,
    getContact,
    deleteContact,
    updateContact
};
