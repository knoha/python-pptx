# encoding: utf-8

"""
Test suite for pptx.opc.package module
"""

from __future__ import absolute_import

import pytest

from mock import call, Mock, patch, PropertyMock

from pptx.opc.oxml import CT_Relationships
from pptx.opc.packuri import PackURI
from pptx.opc.package import (
    Part, PartFactory, _Relationship, RelationshipCollection, Unmarshaller
)

from ..unitutil import (
    absjoin, class_mock, instance_mock, method_mock, test_file_dir
)


test_pptx_path = absjoin(test_file_dir, 'test.pptx')
dir_pkg_path = absjoin(test_file_dir, 'expanded_pptx')
zip_pkg_path = test_pptx_path


@pytest.fixture
def tmp_pptx_path(tmpdir):
    return str(tmpdir.join('test_python-pptx.pptx'))

# def test_it_finds_default_case_insensitive(self, cti):
#     """_ContentTypesItem[partname] finds default case insensitive"""
#     # setup ------------------------
#     partname = '/ppt/media/image1.JPG'
#     content_type = 'image/jpeg'
#     cti._defaults = {'jpg': content_type}
#     # exercise ---------------------
#     val = cti[partname]
#     # verify -----------------------
#     assert val == content_type

# def test_it_finds_override_case_insensitive(self, cti):
#     """_ContentTypesItem[partname] finds override case insensitive"""
#     # setup ------------------------
#     partname = '/foo/bar.xml'
#     case_mangled_partname = '/FoO/bAr.XML'
#     content_type = 'application/vnd.content_type'
#     cti._overrides = {
#         partname: content_type
#     }
#     # exercise ---------------------
#     val = cti[case_mangled_partname]
#     # verify -----------------------
#     assert val == content_type

# def test_save_accepts_stream(self, tmp_pptx_path):
#     pkg = Package().open(dir_pkg_path)
#     stream = StringIO()
#     # exercise --------------------
#     pkg.save(stream)
#     # verify ----------------------
#     # can't use is_zipfile() directly on stream in Python 2.6
#     stream.seek(0)
#     with open(tmp_pptx_path, 'wb') as f:
#         f.write(stream.read())
#     msg = "Package.save(stream) did not create zipfile"
#     assert is_zipfile(tmp_pptx_path), msg


class DescribePart(object):

    def it_remembers_its_construction_state(self):
        partname, content_type, blob = (
            Mock(name='partname'), Mock(name='content_type'),
            Mock(name='blob')
        )
        part = Part(partname, content_type, blob)
        assert part.blob == blob
        assert part.content_type == content_type
        assert part.partname == partname

    def it_has_a_rels_collection_initialized_on_first_reference(
            self, RelationshipCollection_):
        partname = PackURI('/foo/bar.xml')
        part = Part(partname, None, None)
        assert part._rels == RelationshipCollection_.return_value
        RelationshipCollection_.assert_called_once_with(partname.baseURI)

    def it_can_add_a_relationship_to_another_part(self, part):
        # mockery ----------------------
        reltype, target, rId = (
            Mock(name='reltype'), Mock(name='target'), Mock(name='rId')
        )
        setattr(part, '__rels', Mock(name='_rels'))
        # exercise ---------------------
        part._add_relationship(reltype, target, rId)
        # verify -----------------------
        part._rels.add_relationship.assert_called_once_with(
            reltype, target, rId, False
        )

    def it_can_be_notified_after_unmarshalling_is_complete(self, part):
        part._after_unmarshal()

    def it_can_be_notified_before_marshalling_is_started(self, part):
        part._before_marshal()

    # fixtures ---------------------------------------------

    @pytest.fixture
    def part(self):
        partname = PackURI('/foo/bar.xml')
        return Part(partname, None, None)

    @pytest.fixture
    def RelationshipCollection_(self, request):
        return class_mock(request, 'pptx.opc.package.RelationshipCollection')


class DescribePartFactory(object):

    def it_constructs_custom_part_type_for_registered_content_types(
            self, part_args_, CustomPartClass_, part_of_custom_type_):
        partname, content_type, blob = part_args_
        PartFactory.part_type_for[content_type] = CustomPartClass_
        part = PartFactory(partname, content_type, blob)
        CustomPartClass_.load.assert_called_once_with(
            partname, content_type, blob
        )
        assert part is part_of_custom_type_

    def it_constructs_part_using_default_class_when_no_custom_registered(
            self, part_args_, DefaultPartClass_, part_of_default_type_):
        # fixture ----------------------
        partname, content_type, blob = part_args_
        # default_part_type needs to be set back after test
        _prior_def_part_type = PartFactory.default_part_type
        # exercise ---------------------
        PartFactory.default_part_type = DefaultPartClass_
        part = PartFactory(partname, content_type, blob)
        # teardown ---------------------
        PartFactory.default_part_type = _prior_def_part_type
        # verify -----------------------
        DefaultPartClass_.load.assert_called_once_with(
            partname, content_type, blob
        )
        assert part is part_of_default_type_

    # fixtures ---------------------------------------------

    @pytest.fixture
    def part_of_custom_type_(self, request):
        return instance_mock(request, Part)

    @pytest.fixture
    def CustomPartClass_(self, request, part_of_custom_type_):
        CustomPartClass_ = Mock(name='CustomPartClass', spec=Part)
        CustomPartClass_.load.return_value = part_of_custom_type_
        return CustomPartClass_

    @pytest.fixture
    def part_of_default_type_(self, request):
        return instance_mock(request, Part)

    @pytest.fixture
    def DefaultPartClass_(self, part_of_default_type_):
        DefaultPartClass_ = Mock(name='DefaultPartClass', spec=Part)
        DefaultPartClass_.load.return_value = part_of_default_type_
        return DefaultPartClass_

    @pytest.fixture
    def part_args_(self, request):
        partname_ = instance_mock(request, PackURI, name="partname_")
        content_type_ = instance_mock(request, str, name="content_type_")
        blob_ = instance_mock(request, str, name="blob_")
        return partname_, content_type_, blob_


class Describe_Relationship(object):

    def it_remembers_construction_values(self):
        # test data --------------------
        rId = 'rId9'
        reltype = 'reltype'
        target = Mock(name='target_part')
        external = False
        # exercise ---------------------
        rel = _Relationship(rId, reltype, target, None, external)
        # verify -----------------------
        assert rel.rId == rId
        assert rel.reltype == reltype
        assert rel.target_part == target
        assert rel.is_external == external

    def it_should_raise_on_target_part_access_on_external_rel(self):
        rel = _Relationship(None, None, None, None, external=True)
        with pytest.raises(ValueError):
            rel.target_part

    def it_should_have_target_ref_for_external_rel(self):
        rel = _Relationship(None, None, 'target', None, external=True)
        assert rel.target_ref == 'target'

    def it_should_have_relative_ref_for_internal_rel(self):
        """
        Internal relationships (TargetMode == 'Internal' in the XML) should
        have a relative ref, e.g. '../slideLayouts/slideLayout1.xml', for
        the target_ref attribute.
        """
        part = Mock(name='part', partname=PackURI('/ppt/media/image1.png'))
        baseURI = '/ppt/slides'
        rel = _Relationship(None, None, part, baseURI)  # external=False
        assert rel.target_ref == '../media/image1.png'


class DescribeRelationshipCollection(object):

    def it_has_a_len(self):
        rels = RelationshipCollection(None)
        assert len(rels) == 0

    def it_supports_indexed_access(self):
        rels = RelationshipCollection(None)
        try:
            rels[0]
        except TypeError:
            msg = 'RelationshipCollection does not support indexed access'
            pytest.fail(msg)
        except IndexError:
            pass

    def it_has_dict_style_lookup_of_rel_by_rId(self):
        rel = Mock(name='rel', rId='foobar')
        rels = RelationshipCollection(None)
        rels._rels.append(rel)
        assert rels['foobar'] == rel

    def it_should_raise_on_failed_lookup_by_rId(self):
        rel = Mock(name='rel', rId='foobar')
        rels = RelationshipCollection(None)
        rels._rels.append(rel)
        with pytest.raises(KeyError):
            rels['barfoo']

    def it_can_add_a_relationship(self, _Relationship_):
        baseURI, rId, reltype, target, external = (
            'baseURI', 'rId9', 'reltype', 'target', False
        )
        rels = RelationshipCollection(baseURI)
        rel = rels.add_relationship(reltype, target, rId, external)
        _Relationship_.assert_called_once_with(rId, reltype, target, baseURI,
                                               external)
        assert rels[0] == rel
        assert rel == _Relationship_.return_value

    def it_can_compose_rels_xml(self, rels, rels_elm):
        # exercise ---------------------
        rels.xml
        # trace ------------------------
        print('Actual calls:\n%s' % rels_elm.mock_calls)
        # verify -----------------------
        expected_rels_elm_calls = [
            call.add_rel('rId1', 'http://rt-hyperlink', 'http://some/link',
                         True),
            call.add_rel('rId2', 'http://rt-image', '../media/image1.png',
                         False),
            call.xml()
        ]
        assert rels_elm.mock_calls == expected_rels_elm_calls

    # fixtures ---------------------------------------------

    @pytest.fixture
    def _Relationship_(self, request):
        return class_mock(request, 'pptx.opc.package._Relationship')

    @pytest.fixture
    def rels(self):
        """
        Populated RelationshipCollection instance that will exercise the
        rels.xml property.
        """
        rels = RelationshipCollection('/baseURI')
        rels.add_relationship(
            reltype='http://rt-hyperlink', target='http://some/link',
            rId='rId1', is_external=True
        )
        part = Mock(name='part')
        part.partname.relative_ref.return_value = '../media/image1.png'
        rels.add_relationship(reltype='http://rt-image', target=part,
                              rId='rId2')
        return rels

    @pytest.fixture
    def rels_elm(self, request):
        """
        Return a rels_elm mock that will be returned from
        CT_Relationships.new()
        """
        # create rels_elm mock with a .xml property
        rels_elm = Mock(name='rels_elm')
        xml = PropertyMock(name='xml')
        type(rels_elm).xml = xml
        rels_elm.attach_mock(xml, 'xml')
        rels_elm.reset_mock()  # to clear attach_mock call
        # patch CT_Relationships to return that rels_elm
        patch_ = patch.object(CT_Relationships, 'new', return_value=rels_elm)
        patch_.start()
        request.addfinalizer(patch_.stop)
        return rels_elm


class DescribeUnmarshaller(object):

    def it_can_unmarshal_from_a_pkg_reader(
            self, _unmarshal_parts, _unmarshal_relationships):
        # mockery ----------------------
        pkg = Mock(name='pkg')
        pkg_reader = Mock(name='pkg_reader')
        part_factory = Mock(name='part_factory')
        parts = {1: Mock(name='part_1'), 2: Mock(name='part_2')}
        _unmarshal_parts.return_value = parts
        # exercise ---------------------
        Unmarshaller.unmarshal(pkg_reader, pkg, part_factory)
        # verify -----------------------
        _unmarshal_parts.assert_called_once_with(pkg_reader, part_factory)
        _unmarshal_relationships.assert_called_once_with(pkg_reader, pkg,
                                                         parts)
        for part in parts.values():
            part.after_unmarshal.assert_called_once_with()

    def it_can_unmarshal_parts(self):
        # test data --------------------
        part_properties = (
            ('/part/name1.xml', 'app/vnd.contentType_A', '<Part_1/>'),
            ('/part/name2.xml', 'app/vnd.contentType_B', '<Part_2/>'),
            ('/part/name3.xml', 'app/vnd.contentType_C', '<Part_3/>'),
        )
        # mockery ----------------------
        pkg_reader = Mock(name='pkg_reader')
        pkg_reader.iter_sparts.return_value = part_properties
        part_factory = Mock(name='part_factory')
        parts = [Mock(name='part1'), Mock(name='part2'), Mock(name='part3')]
        part_factory.side_effect = parts
        # exercise ---------------------
        retval = Unmarshaller._unmarshal_parts(pkg_reader, part_factory)
        # verify -----------------------
        expected_calls = [call(*p) for p in part_properties]
        expected_parts = dict((p[0], parts[idx]) for (idx, p) in
                              enumerate(part_properties))
        assert part_factory.call_args_list == expected_calls
        assert retval == expected_parts

    def it_can_unmarshal_relationships(self):
        # test data --------------------
        reltype = 'http://reltype'
        # mockery ----------------------
        pkg_reader = Mock(name='pkg_reader')
        pkg_reader.iter_srels.return_value = (
            ('/',         Mock(name='srel1', rId='rId1', reltype=reltype,
             target_partname='partname1', is_external=False)),
            ('/',         Mock(name='srel2', rId='rId2', reltype=reltype,
             target_ref='target_ref_1',   is_external=True)),
            ('partname1', Mock(name='srel3', rId='rId3', reltype=reltype,
             target_partname='partname2', is_external=False)),
            ('partname2', Mock(name='srel4', rId='rId4', reltype=reltype,
             target_ref='target_ref_2',   is_external=True)),
        )
        pkg = Mock(name='pkg')
        parts = {}
        for num in range(1, 3):
            name = 'part%d' % num
            part = Mock(name=name)
            parts['partname%d' % num] = part
            pkg.attach_mock(part, name)
        # exercise ---------------------
        Unmarshaller._unmarshal_relationships(pkg_reader, pkg, parts)
        # verify -----------------------
        expected_pkg_calls = [
            call._add_relationship(
                reltype, parts['partname1'], 'rId1', False),
            call._add_relationship(
                reltype, 'target_ref_1', 'rId2', True),
            call.part1._add_relationship(
                reltype, parts['partname2'], 'rId3', False),
            call.part2._add_relationship(
                reltype, 'target_ref_2', 'rId4', True),
        ]
        assert pkg.mock_calls == expected_pkg_calls

    # fixtures ---------------------------------------------

    @pytest.fixture
    def _unmarshal_parts(self, request):
        return method_mock(request, Unmarshaller, '_unmarshal_parts')

    @pytest.fixture
    def _unmarshal_relationships(self, request):
        return method_mock(request, Unmarshaller, '_unmarshal_relationships')
